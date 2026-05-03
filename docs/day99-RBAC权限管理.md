# Day 99: RBAC 权限管理

> 📅 日期：2026-05-03
> 📖 学习主题：RBAC 权限管理（Role/ClusterRole, RoleBinding/ClusterRoleBinding, ServiceAccount, 最小权限原则, 审计日志）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 91 Kubernetes Pod, Day 95 Kubernetes Service, Day 97 ConfigMap 与 Secret

## 🎯 学习目标

完成 Day 99 的学习后，你应该能够：

1. 深入理解 Kubernetes RBAC 的架构和工作原理
2. 掌握 Role/ClusterRole 和 RoleBinding/ClusterRoleBinding 的使用
3. 能够设计和实现最小权限原则的访问控制策略
4. 了解 ServiceAccount 的使用场景和安全最佳实践
5. 配置和分析 Kubernetes 审计日志

---

## 📖 核心知识点

### 1. RBAC 概述

#### 1.1 什么是 RBAC

```
RBAC（Role-Based Access Control）= 基于角色的访问控制

核心思想：
  - 不直接给用户分配权限
  - 先定义角色（Role），每个角色有一组权限
  - 再将角色绑定（Binding）到用户或组

Kubernetes RBAC 的四个核心对象：
  Role        →  命名空间级别的权限定义
  ClusterRole →  集群级别的权限定义
  RoleBinding  →  将 Role 绑定到用户/组/SA
  ClusterRoleBinding →  将 ClusterRole 绑定到用户/组/SA
```

#### 1.2 RBAC 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes RBAC 架构                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    认证（Authentication）              │  │
│  │  确定"你是谁"                                         │  │
│  │  - X.509 证书                                        │  │
│  │  - ServiceAccount Token                              │  │
│  │  - OIDC Token                                        │  │
│  │  - Webhook Token                                     │  │
│  └──────────────────────────┬───────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    授权（Authorization）               │  │
│  │  确定"你能做什么"                                     │  │
│  │                                                      │  │
│  │  ┌─────────────┐    ┌──────────────┐                 │  │
│  │  │   Role /    │    │   User /     │                 │  │
│  │  │ ClusterRole │    │   Group /    │                 │  │
│  │  │             │    │ ServiceAccount│                │  │
│  │  └──────┬──────┘    └──────┬───────┘                 │  │
│  │         │                  │                         │  │
│  │         └────────┬─────────┘                         │  │
│  │                  │                                    │  │
│  │                  ▼                                    │  │
│  │  ┌──────────────────────────────────────┐            │  │
│  │  │  RoleBinding / ClusterRoleBinding    │            │  │
│  │  │  (绑定 Role 到 User/Group/SA)        │            │  │
│  │  └──────────────────────────────────────┘            │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    准入控制（Admission Control）       │  │
│  │  - ValidatingWebhook                                 │  │
│  │  - MutatingWebhook                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 RBAC vs ABAC

| 特性 | RBAC | ABAC |
|------|------|------|
| 配置方式 | Kubernetes API 对象 | 策略文件 |
| 动态更新 | 支持（kubectl apply） | 需要重启 API Server |
| 粒度 | 角色级别 | 属性级别 |
| 复杂度 | 低 | 高 |
| 推荐度 | 推荐 | 已弃用 |

---

### 2. Role（命名空间级别）

#### 2.1 Role 定义

```yaml
# 允许读取 default 命名空间中的 Pod
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
  - apiGroups: [""]           # "" 表示核心 API 组（Pod, Service 等）
    resources: ["pods"]       # 资源类型
    verbs: ["get", "list", "watch"]  # 允许的操作
---
# 允许管理 Deployment
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-manager
  namespace: production
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments/scale"]    # 子资源
    verbs: ["update", "patch"]
---
# 允许读取 ConfigMap 和 Secret
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: config-reader
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list", "watch"]
    resourceNames: ["app-config", "db-credentials"]  # 只允许访问特定资源
```

#### 2.2 verbs（动词）详解

| 动词 | HTTP 方法 | 说明 |
|------|-----------|------|
| get | GET | 获取单个资源 |
| list | GET (集合) | 列出资源列表 |
| watch | GET (watch) | 监听资源变化 |
| create | POST | 创建资源 |
| update | PUT | 更新整个资源 |
| patch | PATCH | 部分更新资源 |
| delete | DELETE | 删除单个资源 |
| deletecollection | DELETE (集合) | 批量删除资源 |

#### 2.3 apiGroups 说明

```
核心 API 组（apiGroups: [""]）：
  Pod, Service, ConfigMap, Secret, Namespace, Node, PV, PVC 等

apps 组（apiGroups: ["apps"]）：
  Deployment, StatefulSet, DaemonSet, ReplicaSet

batch 组（apiGroups: ["batch"]）：
  Job, CronJob

networking.k8s.io 组（apiGroups: ["networking.k8s.io"]）：
  Ingress, NetworkPolicy

rbac.authorization.k8s.io 组（apiGroups: ["rbac.authorization.k8s.io"]）：
  Role, ClusterRole, RoleBinding, ClusterRoleBinding

storage.k8s.io 组（apiGroups: ["storage.k8s.io"]）：
  StorageClass, CSIDriver

所有资源（特殊值）：
  resources: ["*"]     # 所有资源
  apiGroups: ["*"]     # 所有 API 组
  verbs: ["*"]         # 所有操作
```

---

### 3. ClusterRole（集群级别）

#### 3.1 ClusterRole 定义

```yaml
# 集群级别的只读权限
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "namespaces"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["get", "list", "watch"]
---
# 节点管理权限
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-admin
rules:
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: [""]
    resources: ["nodes/status"]
    verbs: ["update", "patch"]
---
# 集群管理员（所有权限）
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-admin-custom
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
  - nonResourceURLs: ["*"]    # 非资源 URL（如 /healthz）
    verbs: ["*"]
```

#### 3.2 Role vs ClusterRole

| 特性 | Role | ClusterRole |
|------|------|-------------|
| 作用范围 | 单个命名空间 | 集群所有命名空间 |
| 绑定方式 | RoleBinding | RoleBinding 或 ClusterRoleBinding |
| 适用资源 | 命名空间资源 | 命名空间资源 + 集群资源（Node, PV, Namespace） |
| 定义位置 | 必须指定 namespace | 无 namespace |

```
何时使用 ClusterRole：
  1. 需要访问集群资源（Node, PV, Namespace, ClusterRole）
  2. 需要跨命名空间的相同权限
  3. 需要访问非资源 URL（/healthz, /metrics）

何时使用 Role：
  1. 权限仅限于特定命名空间
  2. 不同命名空间需要不同权限
  3. 遵循最小权限原则
```

---

### 4. RoleBinding 与 ClusterRoleBinding

#### 4.1 RoleBinding 定义

```yaml
# 将 Role 绑定到用户
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods-binding
  namespace: default
subjects:
  - kind: User
    name: alice
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
---
# 将 Role 绑定到组
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-team-binding
  namespace: development
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: deployment-manager
  apiGroup: rbac.authorization.k8s.io
---
# 将 ClusterRole 绑定到特定命名空间的用户
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: admin-binding
  namespace: production
subjects:
  - kind: User
    name: bob
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole          # 引用 ClusterRole
  name: admin                # 但只在 production 命名空间生效
  apiGroup: rbac.authorization.k8s.io
```

#### 4.2 ClusterRoleBinding 定义

```yaml
# 集群级别的绑定
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-admin-binding
subjects:
  - kind: User
    name: admin
    apiGroup: rbac.authorization.k8s.io
  - kind: Group
    name: system:admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
```

#### 4.3 Binding 的三种 subject 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| User | 用户（外部身份） | alice, bob, admin |
| Group | 用户组 | dev-team, ops-team, system:authenticated |
| ServiceAccount | 服务账户（Pod 身份） | default, myapp-sa |

```
特殊用户/组：

system:anonymous        →  未认证的请求
system:authenticated    →  所有已认证的用户
system:serviceaccounts  →  所有 ServiceAccount
system:masters          →  超级管理员组（绕过 RBAC）
```

---

### 5. ServiceAccount

#### 5.1 ServiceAccount 概述

```
ServiceAccount（SA）是 Kubernetes 中 Pod 的身份标识。

用途：
  1. Pod 访问 Kubernetes API
  2. Pod 访问其他需要认证的服务
  3. 实现最小权限原则（每个应用独立的 SA）

默认行为：
  - 每个命名空间有一个 default SA
  - Pod 默认使用 default SA
  - SA Token 自动挂载到 Pod（/var/run/secrets/kubernetes.io/serviceaccount/）
```

#### 5.2 创建 ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
  labels:
    app: myapp
    team: backend
# 可选：自动挂载 Token
automountServiceAccountToken: true
```

#### 5.3 使用 ServiceAccount

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  namespace: production
spec:
  serviceAccountName: myapp-sa    # 指定 ServiceAccount
  automountServiceAccountToken: true  # 自动挂载 Token
  containers:
    - name: myapp
      image: myapp:1.0
      volumeMounts:
        - name: sa-token
          mountPath: /var/run/secrets/kubernetes.io/serviceaccount
          readOnly: true
  volumes:
    - name: sa-token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600    # Token 过期时间
              audience: kubernetes        # Token 受众
```

#### 5.4 ServiceAccount Token 安全最佳实践

```
传统 Token（长期有效）：
  - 自动生成，存储在 Secret 中
  - 不过期，安全风险高
  - Kubernetes 1.24+ 默认不再自动创建

Bound Token（推荐）：
  - 手动创建，绑定到特定 Pod
  - 可设置过期时间
  - 支持 audience 限制
  - 更安全
```

```yaml
# 手动创建 Bound ServiceAccount Token
apiVersion: v1
kind: Secret
metadata:
  name: myapp-token
  annotations:
    kubernetes.io/service-account.name: myapp-sa
type: kubernetes.io/service-account-token
```

#### 5.5 禁用自动 Token 挂载

```yaml
# 方式 1：ServiceAccount 级别
apiVersion: v1
kind: ServiceAccount
metadata:
  name: no-token-sa
automountServiceAccountToken: false    # 禁用

---
# 方式 2：Pod 级别（覆盖 SA 设置）
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  automountServiceAccountToken: false  # 禁用
  containers:
    - name: app
      image: myapp:1.0
```

---

### 6. 最小权限原则

#### 6.1 设计原则

```
最小权限原则（Principle of Least Privilege）：

  每个用户/服务只应拥有完成其工作所需的最小权限。

在 Kubernetes 中的应用：
  1. 不使用 cluster-admin 进行日常操作
  2. 为每个应用创建独立的 ServiceAccount
  3. 只授予必要的 verbs（不使用 *）
  4. 限制资源范围（resourceNames）
  5. 使用命名空间隔离不同环境
  6. 定期审计权限
```

#### 6.2 常见角色模板

```yaml
# 只读用户（开发人员）
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-readonly
  namespace: development
rules:
  - apiGroups: ["", "apps", "batch"]
    resources: ["pods", "services", "deployments", "configmaps", "jobs"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]      # 允许查看日志
    verbs: ["get"]
---
# CI/CD 服务账户
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: cicd-deployer
  namespace: production
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: ["apps"]
    resources: ["deployments/status"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list"]
---
# 监控服务账户
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "nodes", "endpoints"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec", "pods/portforward"]  # 明确禁止
    verbs: []                                       # 不允许任何操作
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch"]
  - nonResourceURLs: ["/metrics"]
    verbs: ["get"]
```

#### 6.3 权限审计脚本

```bash
#!/bin/bash
# rbac-audit.sh - 审计 RBAC 权限

echo "=== ClusterRole 绑定到 system:anonymous ==="
kubectl get clusterrolebindings -o json | jq -r '
  .items[] |
  select(.subjects[]? | select(.name == "system:anonymous")) |
  .metadata.name + " -> " + .roleRef.name
'

echo ""
echo "=== 使用 * 权限的 Role/ClusterRole ==="
kubectl get clusterroles -o json | jq -r '
  .items[] |
  select(.rules[]? | select(.verbs[]? == "*" or .resources[]? == "*")) |
  .metadata.name
'

echo ""
echo "=== ServiceAccount Token 过期策略 ==="
kubectl get serviceaccounts --all-namespaces -o json | jq -r '
  .items[] |
  select(.automountServiceAccountToken != false) |
  .metadata.namespace + "/" + .metadata.name + " (auto-mount: true)"
'

echo ""
echo "=== Role 绑定到 system:serviceaccounts:default ==="
kubectl get rolebindings --all-namespaces -o json | jq -r '
  .items[] |
  select(.subjects[]? | select(.name == "default" and .kind == "ServiceAccount")) |
  .metadata.namespace + "/" + .metadata.name + " -> " + .roleRef.name
'
```

---

### 7. 内置 ClusterRole

Kubernetes 提供了一组内置的 ClusterRole：

| ClusterRole | 说明 |
|-------------|------|
| cluster-admin | 超级管理员，拥有所有权限 |
| admin | 命名空间管理员（不包括 ResourceQuota 和 Namespace 本身） |
| edit | 命名空间编辑权限（不包括 Role 和 RoleBinding） |
| view | 命名空间只读权限（不包括 Secret） |
| system:discovery | 公开的 API 发现信息 |
| system:public-info-viewer | 集群公开信息只读 |

```yaml
# 使用内置 ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-team-edit
  namespace: development
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit                    # 使用内置的 edit 角色
  apiGroup: rbac.authorization.k8s.io
```

---

### 8. 审计日志

#### 8.1 审计日志概述

```
Kubernetes 审计日志记录了 API Server 收到的所有请求。

审计日志记录的信息：
  - 谁（User/SA）发起了请求
  - 什么时候发的
  - 访问了什么资源
  - 执行了什么操作
  - 从哪个 IP 发起的
  - 请求的结果（成功/失败）
```

#### 8.2 审计策略配置

```yaml
# /etc/kubernetes/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # 不记录对某些资源的请求
  - level: None
    resources:
      - group: ""
        resources: ["endpoints", "services", "services/status"]
    users: ["system:kube-proxy"]
    verbs: ["watch"]

  # 不记录某些非资源 URL
  - level: None
    nonResourceURLs:
      - "/healthz*"
      - "/version"
      - "/swagger*"

  # 只记录元数据级别（不记录请求体和响应体）
  - level: Metadata
    resources:
      - group: ""
        resources: ["secrets", "configmaps"]
    omitStages:
      - "RequestReceived"

  # 记录对 RBAC 资源的完整请求
  - level: RequestResponse
    resources:
      - group: "rbac.authorization.k8s.io"

  # 记录认证失败
  - level: Metadata
    resources:
      - group: "authentication.k8s.io"

  # 其他请求只记录元数据
  - level: Metadata
    omitStages:
      - "RequestReceived"
```

#### 8.3 审计级别

| 级别 | 记录内容 |
|------|----------|
| None | 不记录 |
| Metadata | 请求元数据（用户、资源、操作、时间） |
| Request | 元数据 + 请求体 |
| RequestResponse | 元数据 + 请求体 + 响应体 |

#### 8.4 启用审计日志

```yaml
# kube-apiserver 启动参数
--audit-policy-file=/etc/kubernetes/audit-policy.yaml
--audit-log-path=/var/log/kubernetes/audit.log
--audit-log-maxage=30           # 保留天数
--audit-log-maxbackup=10        # 备份文件数
--audit-log-maxsize=100         # 单个文件大小（MB）
--audit-log-format=json         # 日志格式
```

#### 8.5 审计日志分析

```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "RequestResponse",
  "auditID": "abc123-def456",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/default/secrets",
  "verb": "create",
  "user": {
    "username": "admin",
    "groups": ["system:masters"]
  },
  "sourceIPs": ["10.0.1.100"],
  "userAgent": "kubectl/v1.28.0",
  "objectRef": {
    "resource": "secrets",
    "namespace": "default",
    "name": "db-credentials"
  },
  "responseStatus": {
    "metadata": {},
    "code": 201
  },
  "requestReceivedTimestamp": "2026-05-03T10:30:00.000Z",
  "stageTimestamp": "2026-05-03T10:30:00.100Z"
}
```

```bash
# 分析审计日志
# 查看所有创建 Secret 的请求
cat /var/log/kubernetes/audit.log | jq 'select(.verb == "create" and .objectRef.resource == "secrets")'

# 查看认证失败的请求
cat /var/log/kubernetes/audit.log | jq 'select(.responseStatus.code == 401 or .responseStatus.code == 403)'

# 查看特定用户的操作
cat /var/log/kubernetes/audit.log | jq 'select(.user.username == "admin")'

# 查看特定命名空间的操作
cat /var/log/kubernetes/audit.log | jq 'select(.objectRef.namespace == "production")'
```

---

### 9. RBAC 安全最佳实践

#### 9.1 安全检查清单

```
RBAC 安全检查清单：

1. 避免使用 cluster-admin
   - 不要将 cluster-admin 绑定到普通用户
   - 不要在 CI/CD 中使用 cluster-admin
   - 使用内置的 admin/edit/view 角色

2. 限制 system:anonymous
   - 确保匿名用户没有敏感权限
   - 检查 system:public-info-viewer

3. ServiceAccount 安全
   - 不使用 default SA
   - 为每个应用创建独立 SA
   - 禁用不需要的 Token 自动挂载
   - 使用 Bound Token

4. 定期审计
   - 检查是否有过度授权
   - 检查不再使用的绑定
   - 检查 ServiceAccount Token

5. 命名空间隔离
   - 不同环境使用不同命名空间
   - 限制跨命名空间访问
   - 使用 NetworkPolicy 隔离网络
```

#### 9.2 常见安全问题

```yaml
# 问题 1：过度授权
# 错误：给开发人员集群管理员权限
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: dev-admin
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cluster-admin     # 危险！
  apiGroup: rbac.authorization.k8s.io
---
# 正确：只给开发人员特定命名空间的编辑权限
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-edit
  namespace: development
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit              # 限制在 development 命名空间
  apiGroup: rbac.authorization.k8s.io
```

```yaml
# 问题 2：default ServiceAccount 过度授权
# 错误：给 default SA 授权
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: default-sa-admin
  namespace: production
subjects:
  - kind: ServiceAccount
    name: default         # 危险！所有 Pod 默认使用此 SA
    namespace: production
roleRef:
  kind: Role
  name: admin
  apiGroup: rbac.authorization.k8s.io
---
# 正确：为特定应用创建独立 SA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: myapp-sa        # 只给特定 SA
    namespace: production
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io
```

---

### 10. RBAC 调试与排错

#### 10.1 常见问题

```
问题 1：Forbidden (403)
  原因：RBAC 权限不足
  排查：
    kubectl auth can-i <verb> <resource> --as=<user>
    kubectl get rolebindings,clusterrolebindings -A | grep <user>
    kubectl describe rolebinding <binding-name>

问题 2：RBAC 规则不生效
  原因：
  - Role/RoleBinding 的 namespace 不匹配
  - Role 的 apiGroups 或 resources 不正确
  - 用户名/组名拼写错误
  排查：
    kubectl auth can-i list pods --as=system:serviceaccount:default:myapp-sa

问题 3：ServiceAccount Token 无效
  原因：
  - Token 已过期
  - Token 未正确挂载
  - ServiceAccount 被删除
  排查：
    kubectl get sa <name> -o yaml
    kubectl describe pod <name> | grep "Service Account"
```

#### 10.2 调试命令

```bash
# 检查当前用户的权限
kubectl auth can-i list pods
kubectl auth can-i create deployments
kubectl auth can-i '*' '*'  # 检查是否有 cluster-admin 权限

# 检查特定用户的权限
kubectl auth can-i list pods --as=alice
kubectl auth can-i list pods --as=system:serviceaccount:default:myapp-sa

# 检查特定组的权限
kubectl auth can-i list pods --as=alice --as-group=dev-team

# 列出所有 ClusterRole
kubectl get clusterroles

# 列出所有 RoleBinding
kubectl get rolebindings --all-namespaces

# 列出所有 ClusterRoleBinding
kubectl get clusterrolebindings

# 查看特定 Role 的详细信息
kubectl get role <name> -n <namespace> -o yaml

# 查看特定 ClusterRole 的详细信息
kubectl get clusterrole <name> -o yaml

# 检查 ServiceAccount
kubectl get sa --all-namespaces
kubectl describe sa <name> -n <namespace>
```

---

## 💻 实战练习

### 练习 1：基础 RBAC 配置

**目标**：创建用户、角色和绑定

```bash
# 1. 创建命名空间
kubectl create namespace development
kubectl create namespace production

# 2. 创建只读 Role
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: development
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list", "watch"]
EOF

# 3. 创建 RoleBinding
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-read-binding
  namespace: development
subjects:
  - kind: User
    name: alice
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
EOF

# 4. 测试权限
# alice 可以在 development 命名空间查看 Pod
kubectl auth can-i list pods --as=alice -n development    # yes
kubectl auth can-i list pods --as=alice -n production     # no
kubectl auth can-i create pods --as=alice -n development  # no
kubectl auth can-i get secrets --as=alice -n development  # no

# 5. 创建编辑 Role
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-editor
  namespace: development
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "update", "patch"]
  - apiGroups: ["apps"]
    resources: ["deployments/scale"]
    verbs: ["update", "patch"]
EOF

# 6. 给开发团队绑定编辑权限
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-team-edit
  namespace: development
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: deployment-editor
  apiGroup: rbac.authorization.k8s.io
EOF

# 7. 测试组权限
kubectl auth can-i update deployments --as=alice --as-group=dev-team -n development  # yes
kubectl auth can-i delete deployments --as=alice --as-group=dev-team -n development  # no
```

### 练习 2：ServiceAccount 实践

**目标**：创建和使用 ServiceAccount

```bash
# 1. 创建 ServiceAccount
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: default
automountServiceAccountToken: true
EOF

# 2. 创建 Role
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: default
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
    resourceNames: ["myapp-config"]  # 只能访问特定资源
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
EOF

# 3. 绑定 Role 到 SA
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-binding
  namespace: default
subjects:
  - kind: ServiceAccount
    name: myapp-sa
    namespace: default
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io
EOF

# 4. 创建使用该 SA 的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: rbac-test-pod
spec:
  serviceAccountName: myapp-sa
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
EOF

# 5. 在 Pod 中测试权限
kubectl exec rbac-test-pod -- wget -qO- --header="Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  https://kubernetes.default.svc/api/v1/namespaces/default/pods 2>/dev/null || echo "Permission check via API"

# 6. 在集群外测试 SA 权限
kubectl auth can-i list pods --as=system:serviceaccount:default:myapp-sa
kubectl auth can-i list secrets --as=system:serviceaccount:default:myapp-sa
kubectl auth can-i list configmaps --as=system:serviceaccount:default:myapp-sa

# 7. 查看 SA Token
kubectl get secret -n default | grep myapp-sa
kubectl get sa myapp-sa -o yaml
```

### 练习 3：RBAC 安全审计

**目标**：审计集群的 RBAC 配置，发现安全问题

```bash
# 1. 检查所有 ClusterRoleBinding 中的 cluster-admin 绑定
echo "=== Cluster Admin Bindings ==="
kubectl get clusterrolebindings -o json | jq -r '
  .items[] |
  select(.roleRef.name == "cluster-admin") |
  "\(.metadata.name): \(.subjects // [] | map(.kind + "/" + .name) | join(", "))"
'

# 2. 检查 system:anonymous 的权限
echo ""
echo "=== Anonymous User Permissions ==="
kubectl get clusterrolebindings -o json | jq -r '
  .items[] |
  select(.subjects // [] | map(select(.name == "system:anonymous")) | length > 0) |
  .metadata.name + " -> " + .roleRef.name
'

# 3. 检查使用通配符权限的 Role
echo ""
echo "=== Wildcard Permissions ==="
kubectl get roles --all-namespaces -o json | jq -r '
  .items[] |
  select(.rules[]? | select(.verbs[]? == "*" or .resources[]? == "*")) |
  .metadata.namespace + "/" + .metadata.name
'

# 4. 检查 default SA 的绑定
echo ""
echo "=== Default SA Bindings ==="
kubectl get rolebindings --all-namespaces -o json | jq -r '
  .items[] |
  select(.subjects // [] | map(select(.kind == "ServiceAccount" and .name == "default")) | length > 0) |
  .metadata.namespace + "/" + .metadata.name + " -> " + .roleRef.name
'

# 5. 检查未使用的 ServiceAccount
echo ""
echo "=== ServiceAccounts ==="
kubectl get sa --all-namespaces -o json | jq -r '
  .items[] |
  select(.metadata.name != "default") |
  .metadata.namespace + "/" + .metadata.name
'

# 6. 测试匿名用户权限
echo ""
echo "=== Anonymous User Access Test ==="
kubectl auth can-i list pods --as=system:anonymous
kubectl auth can-i list secrets --as=system:anonymous
kubectl auth can-i list nodes --as=system:anonymous

# 7. 生成安全报告
echo ""
echo "=== Security Recommendations ==="
echo "1. 检查上述 cluster-admin 绑定是否必要"
echo "2. 确保 system:anonymous 没有敏感权限"
echo "3. 避免使用通配符权限"
echo "4. 为每个应用创建独立的 ServiceAccount"
echo "5. 定期审计 RBAC 配置"
```

---

## 🎯 面试题精选

### 题目 1：什么是 RBAC？Kubernetes 中如何实现？

**参考答案**：

RBAC（Role-Based Access Control）是基于角色的访问控制模型。

Kubernetes RBAC 的四个核心对象：
1. **Role**：命名空间级别的权限定义，定义可以对哪些资源执行哪些操作
2. **ClusterRole**：集群级别的权限定义，适用于所有命名空间或集群资源
3. **RoleBinding**：将 Role/ClusterRole 绑定到用户/组/ServiceAccount
4. **ClusterRoleBinding**：将 ClusterRole 绑定到用户/组/ServiceAccount（集群范围）

### 题目 2：Role 和 ClusterRole 有什么区别？

**参考答案**：

- **Role**：只能在单个命名空间内定义权限，只能授权命名空间资源
- **ClusterRole**：集群范围的权限定义，可以授权命名空间资源和集群资源（Node、PV、Namespace 等）

使用场景：
- Role：权限仅限于特定命名空间
- ClusterRole：需要访问集群资源或跨命名空间的相同权限

### 题目 3：RoleBinding 和 ClusterRoleBinding 有什么区别？

**参考答案**：

- **RoleBinding**：在单个命名空间内将 Role/ClusterRole 绑定到 subject。如果引用 ClusterRole，权限也只在该命名空间生效。
- **ClusterRoleBinding**：集群范围的绑定，只能引用 ClusterRole，权限在所有命名空间生效。

关键点：RoleBinding 可以引用 ClusterRole，但权限只在 RoleBinding 所在的命名空间生效。这是实现跨命名空间相同权限的常用模式。

### 题目 4：什么是 ServiceAccount？它和普通用户有什么区别？

**参考答案**：

ServiceAccount 是 Kubernetes 中 Pod 的身份标识。

区别：
- **普通用户**：由外部身份系统管理（LDAP、OIDC），不能通过 Kubernetes API 创建
- **ServiceAccount**：由 Kubernetes 管理，可以通过 API 创建和管理

使用场景：
- ServiceAccount：Pod 访问 Kubernetes API、CI/CD 服务
- 普通用户：人类用户通过 kubectl 或 Dashboard 访问

### 题目 5：什么是最小权限原则？如何在 Kubernetes 中实现？

**参考答案**：

最小权限原则：每个用户/服务只应拥有完成其工作所需的最小权限。

实现方式：
1. 不使用 cluster-admin 进行日常操作
2. 为每个应用创建独立的 ServiceAccount
3. 只授予必要的 verbs（不使用 *）
4. 使用 resourceNames 限制特定资源
5. 使用命名空间隔离不同环境
6. 定期审计权限

### 题目 6：如何检查当前用户是否有某个权限？

**参考答案**：

```bash
# 检查当前用户
kubectl auth can-i list pods

# 检查特定用户
kubectl auth can-i list pods --as=alice

# 检查特定命名空间
kubectl auth can-i list pods -n production

# 检查 ServiceAccount
kubectl auth can-i list pods --as=system:serviceaccount:default:myapp-sa

# 检查所有权限
kubectl auth can-i --list
```

### 题目 7：Kubernetes 内置了哪些 ClusterRole？

**参考答案**：

1. **cluster-admin**：超级管理员，拥有所有权限
2. **admin**：命名空间管理员（不包括 ResourceQuota 和 Namespace）
3. **edit**：命名空间编辑权限（不包括 Role 和 RoleBinding）
4. **view**：命名空间只读权限（不包括 Secret）
5. **system:discovery**：公开的 API 发现信息
6. **system:public-info-viewer**：集群公开信息只读

### 题目 8：什么是 Bound ServiceAccount Token？它有什么优势？

**参考答案**：

Bound ServiceAccount Token 是手动创建的、绑定到特定 Pod 的 Token。

优势：
1. **可控过期时间**：可以设置 expirationSeconds
2. **受众限制**：通过 audience 限制 Token 的使用范围
3. **更安全**：Pod 删除后 Token 自动失效
4. **不存储在 Secret 中**：减少泄露风险

Kubernetes 1.24+ 默认不再自动创建长期有效的 SA Token Secret。

### 题目 9：如何审计 Kubernetes 的 RBAC 配置？

**参考答案**：

1. **检查过度授权**：
   - 找出所有 cluster-admin 绑定
   - 找出使用通配符权限的 Role
   - 检查 system:anonymous 的权限

2. **检查 ServiceAccount 安全**：
   - 是否有 default SA 的过度授权
   - SA Token 的过期策略
   - 是否禁用了不必要的自动挂载

3. **使用审计日志**：
   - 启用 API Server 审计日志
   - 记录 RBAC 相关操作
   - 分析认证失败事件

### 题目 10：如何给开发团队配置只读权限？

**参考答案**：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-readonly
  namespace: development
rules:
  - apiGroups: ["", "apps", "batch"]
    resources: ["pods", "services", "deployments", "jobs"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readonly-binding
  namespace: development
subjects:
  - kind: Group
    name: dev-team
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-readonly
  apiGroup: rbac.authorization.k8s.io
```

---

## 📚 深入阅读

- [Kubernetes RBAC 官方文档](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount 文档](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [Kubernetes 审计日志](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/)
- [Kubernetes 认证与授权](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [RBAC 最佳实践](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)

---

## ✅ 自检清单

- [ ] 理解 RBAC 的四个核心对象（Role, ClusterRole, RoleBinding, ClusterRoleBinding）
- [ ] 能够创建 Role 和 ClusterRole 定义权限
- [ ] 能够使用 RoleBinding 和 ClusterRoleBinding 绑定权限
- [ ] 理解 ServiceAccount 的用途和安全最佳实践
- [ ] 能够实现最小权限原则
- [ ] 了解 Kubernetes 内置的 ClusterRole
- [ ] 能够配置和分析审计日志
- [ ] 能够审计集群的 RBAC 配置
- [ ] 能够排查 RBAC 相关的权限问题
