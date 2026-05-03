# Day 102: Helm 包管理器

> 📅 日期：2026-05-03
> 📖 学习主题：Helm Chart 结构、模板语法、values.yaml、仓库管理、发布/回滚、依赖管理、Hook、自定义 Chart
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 93-100（K8s 基础、部署、调度）

## 🎯 学习目标

- 理解 Helm 的核心概念（Chart、Release、Repository）
- 掌握 Helm Chart 的目录结构与文件组织
- 精通 Go 模板语法（条件判断、循环、函数、管道）
- 能够创建自定义 Helm Chart 并管理 values.yaml
- 掌握 Helm 仓库管理与 Chart 分发
- 理解 Helm Hook 机制与生命周期管理
- 能够使用 Helm 进行发布、回滚和依赖管理

---

## 📖 核心知识点

### 1. Helm 核心概念

#### 1.1 Helm 是什么

```
Helm = Kubernetes 的包管理器（类似 apt/yum/npm）

核心概念：
┌──────────────┬──────────────────────────────────────────────┐
│ Chart        │ 一组 K8s 资源模板的打包，类似于 apt 的包      │
│ Repository   │ Chart 的存储仓库，类似于 apt 的源             │
│ Release      │ Chart 的一次部署实例，类似于 apt 安装的包实例  │
│ values.yaml  │ Chart 的默认配置值，类似于包的配置文件         │
└──────────────┴──────────────────────────────────────────────┘

关系图：
Chart (模板) + values (配置) = Release (运行实例)

一个 Chart 可以被多次安装，每次安装创建一个独立的 Release
```

#### 1.2 Helm 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Helm 3 架构                               │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   helm CLI   │───>│  Kubernetes  │───>│  etcd        │  │
│  │  (客户端)     │    │  API Server  │    │  (存储 Release│  │
│  │              │    │              │    │   元数据)     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
│  Helm 2 vs Helm 3：                                          │
│  Helm 2: 客户端 + Tiller（服务端组件）                        │
│  Helm 3: 纯客户端，无 Tiller，Release 信息存储在 K8s Secrets  │
│                                                             │
│  Helm 3 改进：                                               │
│  ✓ 移除 Tiller，更安全                                       │
│  ✓ Release 信息存储在 namespace 的 Secrets 中                 │
│  ✓ 支持 Chart 依赖管理                                       │
│  ✓ 支持 OCI 镜像仓库                                         │
│  ✓ 支持 JSON Schema 验证 values                              │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 安装 Helm

```bash
# 使用官方脚本安装
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 使用 Homebrew 安装（macOS）
brew install helm

# 验证安装
helm version

# 配置 Tab 补全（bash）
source <(helm completion bash)

# 配置 Tab 补全（zsh）
source <(helm completion zsh)
```

---

### 2. Chart 结构详解

#### 2.1 Chart 目录结构

```
mychart/
├── Chart.yaml          # Chart 元数据（名称、版本、描述）
├── Chart.lock          # 依赖锁定文件
├── values.yaml         # 默认配置值
├── values.schema.json  # values 的 JSON Schema 验证
├── templates/          # K8s 资源模板目录
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml
│   ├── serviceaccount.yaml
│   ├── _helpers.tpl    # 模板辅助函数（以 _ 开头）
│   ├── NOTES.txt       # 安装后显示的提示信息
│   └── tests/          # 测试模板
│       └── test-connection.yaml
├── charts/             # 子 Chart 目录
├── crds/               # Custom Resource Definitions
└── README.md           # Chart 说明文档
```

#### 2.2 Chart.yaml 详解

```yaml
# Chart.yaml
apiVersion: v2  # Helm 3 使用 v2，Helm 2 使用 v1
name: my-application  # Chart 名称
version: 1.2.0  # Chart 版本（语义化版本）
appVersion: "2.1.0"  # 应用版本
description: A Helm chart for my application
type: application  # application 或 library
keywords:
  - web
  - nginx
  - api
home: https://github.com/my-org/my-app
sources:
  - https://github.com/my-org/my-app
maintainers:
  - name: SRE Team
    email: sre@example.com
dependencies:
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
```

#### 2.3 values.yaml 设计原则

```yaml
# values.yaml - 默认配置值
# 设计原则：
# 1. 提供合理的默认值
# 2. 使用注释说明每个字段
# 3. 支持环境覆盖（dev/staging/prod）
# 4. 敏感值留空或使用占位符

# 副本数
replicaCount: 2

# 镜像配置
image:
  repository: my-registry.com/my-app
  tag: ""  # 默认使用 Chart.appVersion
  pullPolicy: IfNotPresent

# 镜像拉取凭证
imagePullSecrets: []

# 应用名称（覆盖默认名称）
nameOverride: ""
fullnameOverride: ""

# 服务账户
serviceAccount:
  create: true
  annotations: {}
  name: ""

# Pod 注解
podAnnotations: {}

# Pod 安全上下文
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

# 容器安全上下文
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL

# 服务配置
service:
  type: ClusterIP
  port: 80
  targetPort: 8080

# Ingress 配置
ingress:
  enabled: false
  className: nginx
  annotations: {}
  hosts:
    - host: my-app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []

# 资源限制
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

# HPA 配置
autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# 环境变量
env: {}
#  LOG_LEVEL: info
#  DEBUG: "false"

# ConfigMap 数据
configMap:
  enabled: false
  data: {}

# Secret 数据
secret:
  enabled: false
  data: {}

# 健康检查
livenessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5

# 节点选择器
nodeSelector: {}

# 容忍
tolerations: []

# 亲和性
affinity: {}

# 拓扑分布约束
topologySpreadConstraints: []
```

---

### 3. Go 模板语法

#### 3.1 基础语法

```yaml
# 模板语法基础：
# {{ .Values.xxx }}    - 引用 values.yaml 中的值
# {{ .Release.Name }}  - 引用 Release 名称
# {{ .Chart.AppVersion }} - 引用 Chart 的 appVersion
# {{ include "xxx" . }} - 调用模板函数
# {{- xxx }}           - 去除左侧空白
# {{ xxx -}}           - 去除右侧空白

apiVersion: apps/v1
kind: Deployment
metadata:
  # 使用 include 调用辅助模板生成名称
  name: {{ include "mychart.fullname" . }}
  # 使用 .Release.Namespace 获取命名空间
  namespace: {{ .Release.Namespace }}
  labels:
    # 使用 include 调用通用标签模板
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "mychart.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
```

#### 3.2 条件判断

```yaml
# if/else/with 语法
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "mychart.fullname" . }}
  {{- with .Values.ingress.annotations }}
  annotations:
    # toYaml 将值转换为 YAML 格式
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "mychart.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
```

#### 3.3 循环（range）

```yaml
# range 遍历列表
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "mychart.fullname" . }}-config
data:
  # 遍历 configMap.data 中的键值对
  {{- range $key, $value := .Values.configMap.data }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}

---
# range 遍历环境变量
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          env:
            # 遍历 .Values.env 中的键值对
            {{- range $key, $value := .Values.env }}
            - name: {{ $key }}
              value: {{ $value | quote }}
            {{- end }}
            # 引用 Secret
            {{- if .Values.secret.enabled }}
            {{- range $key, $value := .Values.secret.data }}
            - name: {{ $key }}
              valueFrom:
                secretKeyRef:
                  name: {{ include "mychart.fullname" $ }}-secret
                  key: {{ $key }}
            {{- end }}
            {{- end }}
```

#### 3.4 管道（Pipe）与函数

```yaml
# 管道语法：{{ value | function1 | function2 }}
# 常用函数：

# 1. default - 设置默认值
image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"

# 2. quote - 添加引号
name: {{ .Values.name | quote }}

# 3. nindent - 缩进（带换行）
annotations:
  {{- toYaml .Values.podAnnotations | nindent 8 }}

# 4. indent - 缩进（不带换行）
data:
  config.yaml: |
    {{- .Values.config | indent 4 }}

# 5. toYaml - 转换为 YAML
spec:
  {{- toYaml .Values.resources | nindent 10 }}

# 6. toJson - 转换为 JSON
metadata:
  annotations:
    config: {{ toJson .Values.config | quote }}

# 7. b64enc/b64dec - Base64 编码/解码
data:
  password: {{ .Values.password | b64enc | quote }}

# 8. sha256sum - 计算 SHA256 哈希
annotations:
  checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}

# 9. trim - 去除空白
value: {{ .Values.value | trim | quote }}

# 10. replace - 替换字符串
value: {{ .Values.value | replace "-" "_" | quote }}

# 11. upper/lower - 大小写转换
value: {{ .Values.value | upper | quote }}

# 12. title - 首字母大写
value: {{ .Values.value | title | quote }}
```

#### 3.5 辅助模板（_helpers.tpl）

```yaml
# templates/_helpers.tpl
# 以 _ 开头的文件不会被渲染为 K8s 资源

# 定义 Chart 名称
{{/*
Define the chart name.
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

# 定义全限定名称（Release-Chart）
{{/*
Create a default fully qualified app name.
*/}}
{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

# 定义 Chart 标签
{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mychart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

# 定义通用标签
{{/*
Common labels
*/}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

# 定义选择器标签
{{/*
Selector labels
*/}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

# 定义 ServiceAccount 名称
{{/*
Create the name of the service account to use
*/}}
{{- define "mychart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mychart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

#### 3.6 NOTES.txt

```yaml
# templates/NOTES.txt
# 安装后显示的提示信息

Thank you for installing {{ include "mychart.fullname" . }}!

Your release is named {{ .Release.Name }}.

To get the application URL:
{{- if .Values.ingress.enabled }}
{{- range $host := .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ $host.host }}{{ (first $host.paths).path }}
{{- end }}
{{- else if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "mychart.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "LoadBalancer" .Values.service.type }}
  NOTE: It may take a few minutes for the LoadBalancer IP to be available.
  kubectl get --namespace {{ .Release.Namespace }} svc {{ include "mychart.fullname" . }} -w
{{- else if contains "ClusterIP" .Values.service.type }}
  kubectl --namespace {{ .Release.Namespace }} port-forward svc/{{ include "mychart.fullname" . }} 8080:{{ .Values.service.port }}
  echo http://127.0.0.1:8080
{{- end }}
```

---

### 4. 仓库管理

#### 4.1 仓库操作

```bash
# 添加仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts

# 更新仓库
helm repo update

# 查看仓库列表
helm repo list

# 搜索 Chart
helm search repo nginx
helm search repo bitnami/nginx
helm search repo bitnami/nginx --versions

# 查看 Chart 信息
helm show chart bitnami/nginx
helm show values bitnami/nginx
helm show readme bitnami/nginx
helm show all bitnami/nginx

# 删除仓库
helm repo remove bitnami
```

#### 4.2 OCI 仓库（Helm 3.8+）

```bash
# OCI 仓库：使用容器镜像仓库存储 Chart
# 支持 Docker Hub、GitHub Container Registry、AWS ECR、阿里云 ACR 等

# 登录 OCI 仓库
helm registry login ghcr.io -u username -p password

# 推送 Chart 到 OCI 仓库
helm push mychart-1.0.0.tgz oci://ghcr.io/my-org/charts

# 从 OCI 仓库安装
helm install my-release oci://ghcr.io/my-org/charts/mychart --version 1.0.0

# 拉取 Chart
helm pull oci://ghcr.io/my-org/charts/mychart --version 1.0.0
```

#### 4.3 自建 Chart 仓库

```bash
# 方案 1：使用 GitHub Pages
# 将 Chart 打包后上传到 GitHub 仓库
# 使用 GitHub Pages 托管 index.yaml

# 方案 2：使用 chartmuseum
docker run -d \
  -p 8080:8080 \
  -e STORAGE=local \
  -e STORAGE_LOCAL_ROOTDIR=/charts \
  -v /data/charts:/charts \
  chartmuseum/chartmuseum

# 添加自建仓库
helm repo add my-repo http://localhost:8080

# 推送 Chart 到 chartmuseum
curl --data-binary "@mychart-1.0.0.tgz" http://localhost:8080/api/charts

# 方案 3：使用 Harbor（推荐生产环境）
# Harbor 内置了 Helm Chart 仓库支持
```

---

### 5. 发布与回滚

#### 5.1 Helm 安装与升级

```bash
# 安装 Chart
helm install my-release bitnami/nginx \
  --namespace production \
  --create-namespace \
  --set replicaCount=3 \
  --set service.type=ClusterIP

# 使用 values 文件安装
helm install my-release bitnami/nginx \
  -f values.yaml \
  -f values-production.yaml \
  --namespace production

# 使用 --set 设置值（优先级最高）
helm install my-release bitnami/nginx \
  --set replicaCount=3 \
  --set image.tag=1.25 \
  --set resources.requests.cpu=100m

# 升级 Release
helm upgrade my-release bitnami/nginx \
  --namespace production \
  --set replicaCount=5 \
  --set image.tag=1.26

# 安装或升级（如果不存在则安装）
helm upgrade --install my-release bitnami/nginx \
  --namespace production \
  --set replicaCount=3

# 使用 --wait 等待所有 Pod 就绪
helm upgrade --install my-release bitnami/nginx \
  --namespace production \
  --wait \
  --timeout 5m

# 使用 --atomic 在失败时自动回滚
helm upgrade --install my-release bitnami/nginx \
  --namespace production \
  --atomic \
  --timeout 5m
```

#### 5.2 values 文件优先级

```
优先级从高到低：
1. --set 命令行参数
2. --set-file 命令行参数
3. --set-string 命令行参数
4. -f / --values 文件参数（后添加的优先级更高）
5. Chart 中的 values.yaml（默认值）

示例：
helm install my-release mychart \
  -f values.yaml \          # 优先级 4
  -f values-prod.yaml \     # 优先级 3（覆盖 values.yaml）
  --set replicaCount=5      # 优先级 1（最高优先级）
```

#### 5.3 Helm 回滚

```bash
# 查看 Release 历史
helm history my-release -n production

# 回滚到上一个版本
helm rollback my-release -n production

# 回滚到指定版本
helm rollback my-release 2 -n production

# 回滚时等待 Pod 就绪
helm rollback my-release 2 -n production --wait --timeout 5m

# 查看回滚后的状态
helm status my-release -n production
```

#### 5.4 Release 管理

```bash
# 查看所有 Release
helm list -A

# 查看指定 namespace 的 Release
helm list -n production

# 查看 Release 状态
helm status my-release -n production

# 查看 Release 的 values
helm get values my-release -n production

# 查看 Release 的所有 values（包括默认值）
helm get values my-release -n production --all

# 查看 Release 生成的清单
helm get manifest my-release -n production

# 查看 Release 的 hooks
helm get hooks my-release -n production

# 查看 Release 的 notes
helm get notes my-release -n production

# 卸载 Release
helm uninstall my-release -n production

# 卸载但保留历史
helm uninstall my-release -n production --keep-history
```

---

### 6. 依赖管理

#### 6.1 Chart 依赖配置

```yaml
# Chart.yaml 中的 dependencies
dependencies:
  # 从 Helm 仓库依赖
  - name: redis
    version: "18.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled  # 条件启用
    tags:                     # 标签
      - cache
      - redis

  # 从 OCI 仓库依赖
  - name: postgresql
    version: "12.x.x"
    repository: "oci://registry-1.docker.io/bitnamicharts/postgresql"
    condition: postgresql.enabled

  # 从本地目录依赖
  - name: common
    version: "1.0.0"
    repository: "file://../common"
```

#### 6.2 依赖管理命令

```bash
# 更新依赖（下载到 charts/ 目录）
helm dependency update mychart/

# 构建依赖（类似 update，但不更新 Chart.lock）
helm dependency build mychart/

# 查看依赖列表
helm dependency list mychart/

# 打包 Chart（包含依赖）
helm package mychart/

# 打包 Chart（不包含依赖，需要运行时下载）
helm package mychart/ --dependency-update
```

#### 6.3 条件依赖与标签

```yaml
# values.yaml 中控制依赖启用
redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: false

postgresql:
  enabled: true
  auth:
    postgresPassword: "changeme"
    database: myapp

# Chart.yaml 中使用条件
dependencies:
  - name: redis
    condition: redis.enabled  # 仅当 redis.enabled=true 时启用
  - name: postgresql
    condition: postgresql.enabled
```

---

### 7. Hook — 生命周期钩子

#### 7.1 Hook 类型

```
Helm Hook 生命周期：

pre-install    → 安装前执行
install        → 安装时执行
post-install   → 安装后执行

pre-upgrade    → 升级前执行
upgrade        → 升级时执行
post-upgrade   → 升级后执行

pre-rollback   → 回滚前执行
rollback       → 回滚时执行
post-rollback  → 回滚后执行

pre-delete     → 删除前执行
delete         → 删除时执行
post-delete    → 删除后执行

test           → 测试时执行（helm test）
```

#### 7.2 Hook 配置示例

```yaml
# 安装前执行数据库迁移
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-db-migrate
  annotations:
    # 指定 Hook 类型
    "helm.sh/hook": pre-install,pre-upgrade
    # Hook 权重（决定执行顺序，数字越小越先执行）
    "helm.sh/hook-weight": "-5"
    # Hook 删除策略
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          command: ["python", "manage.py", "migrate"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: {{ include "mychart.fullname" . }}-db-secret
                  key: url
```

```yaml
# 安装后执行健康检查
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "mychart.fullname" . }}-health-check
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: test
      image: busybox:1.36
      command: ["sh", "-c"]
      args:
        - |
          wget -qO- http://{{ include "mychart.fullname" . }}:{{ .Values.service.port }}/healthz
```

#### 7.3 Hook 删除策略

| 策略 | 含义 |
|------|------|
| before-hook-creation | 新 Hook 执行前删除旧的 Hook 资源 |
| hook-succeeded | Hook 成功后删除 Hook 资源 |
| hook-failed | Hook 失败后删除 Hook 资源 |
| before-hook-creation,hook-succeeded | 创建前删除 + 成功后删除（推荐） |

#### 7.4 SRE 实战：数据库迁移 Hook

```yaml
# templates/job-migrate.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-migrate
  annotations:
    "helm.sh/hook": pre-upgrade
    "helm.sh/hook-weight": "-10"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    metadata:
      labels:
        app.kubernetes.io/component: migration
    spec:
      restartPolicy: Never
      serviceAccountName: {{ include "mychart.serviceAccountName" . }}
      containers:
        - name: migrate
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          command: ["./migrate"]
          args:
            - "--direction=up"
            - "--steps={{ .Values.migration.steps | default 0 }}"
          env:
            - name: DB_HOST
              valueFrom:
                secretKeyRef:
                  name: {{ include "mychart.fullname" . }}-db
                  key: host
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ include "mychart.fullname" . }}-db
                  key: password
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

### 8. 自定义 Chart 实战

#### 8.1 创建 Chart

```bash
# 创建新的 Chart
helm create my-web-app

# 查看生成的结构
tree my-web-app/

# 清理默认模板（保留需要的）
rm my-web-app/templates/ingress.yaml
rm my-web-app/templates/tests/test-connection.yaml
```

#### 8.2 完整的 Deployment 模板

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      annotations:
        # 当 ConfigMap 变更时触发 Pod 重启
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "mychart.selectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "mychart.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds | default 30 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
              protocol: TCP
          {{- with .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- with .Values.env }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          volumeMounts:
            {{- if .Values.configMap.enabled }}
            - name: config
              mountPath: /app/config
              readOnly: true
            {{- end }}
            - name: tmp
              mountPath: /tmp
      volumes:
        {{- if .Values.configMap.enabled }}
        - name: config
          configMap:
            name: {{ include "mychart.fullname" . }}-config
        {{- end }}
        - name: tmp
          emptyDir: {}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.topologySpreadConstraints }}
      topologySpreadConstraints:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

#### 8.3 完整的 Service 模板

```yaml
# templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "mychart.selectorLabels" . | nindent 4 }}
```

#### 8.4 完整的 HPA 模板

```yaml
# templates/hpa.yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "mychart.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
{{- end }}
```

---

### 9. Helm 测试

#### 9.1 测试模板

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "mychart.fullname" . }}-test-connection"
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: wget
      image: busybox:1.36
      command: ['wget']
      args: ['{{ include "mychart.fullname" . }}:{{ .Values.service.port }}']
```

#### 9.2 运行测试

```bash
# 运行 Chart 测试
helm test my-release -n production

# 查看测试日志
helm test my-release -n production --logs
```

---

### 10. Helm 常用技巧

#### 10.1 模板调试

```bash
# 渲染模板（不安装，查看生成的 YAML）
helm template my-release mychart/ -f values.yaml

# 渲染并验证
helm template my-release mychart/ -f values.yaml --validate

# 调试特定模板
helm template my-release mychart/ -f values.yaml -s templates/deployment.yaml

# dry-run 安装（模拟安装）
helm install my-release mychart/ --dry-run --debug

# diff（需要安装 helm-diff 插件）
helm diff upgrade my-release mychart/ -f values.yaml
```

#### 10.2 JSON Schema 验证

```json
// values.schema.json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["replicaCount", "image"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "description": "Number of replicas"
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9./-]*$"
        },
        "tag": {
          "type": "string"
        },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"]
        }
      }
    },
    "resources": {
      "type": "object",
      "properties": {
        "requests": {
          "type": "object",
          "properties": {
            "cpu": { "type": "string" },
            "memory": { "type": "string" }
          }
        },
        "limits": {
          "type": "object",
          "properties": {
            "cpu": { "type": "string" },
            "memory": { "type": "string" }
          }
        }
      }
    }
  }
}
```

#### 10.3 多环境配置

```bash
# 目录结构
environments/
├── dev/
│   └── values.yaml
├── staging/
│   └── values.yaml
└── production/
    └── values.yaml

# 部署到不同环境
helm upgrade --install my-app mychart/ \
  -f values.yaml \
  -f environments/dev/values.yaml \
  -n development

helm upgrade --install my-app mychart/ \
  -f values.yaml \
  -f environments/production/values.yaml \
  -n production
```

```yaml
# environments/dev/values.yaml
replicaCount: 1
image:
  tag: latest
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi

# environments/production/values.yaml
replicaCount: 3
image:
  tag: "2.1.0"
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: "2"
    memory: "2Gi"
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 30
```

---

## 💻 实战练习

### 练习 1：创建基础 Chart

**目标**：从零创建一个完整的 Web 应用 Chart

```bash
# 步骤 1：创建 Chart
helm create my-web-app

# 步骤 2：编辑 Chart.yaml
cat > my-web-app/Chart.yaml << 'EOF'
apiVersion: v2
name: my-web-app
description: A Helm chart for web application
type: application
version: 0.1.0
appVersion: "1.0.0"
maintainers:
  - name: SRE Team
EOF

# 步骤 3：编辑 values.yaml
cat > my-web-app/values.yaml << 'EOF'
replicaCount: 2
image:
  repository: nginx
  tag: "1.25"
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
EOF

# 步骤 4：渲染模板验证
helm template my-release my-web-app/

# 步骤 5：安装
helm install my-release my-web-app/ -n default

# 步骤 6：验证
kubectl get pods -l app.kubernetes.io/instance=my-release
```

### 练习 2：多环境部署

**目标**：为同一 Chart 配置不同环境的 values 文件

```bash
# 创建环境配置文件
mkdir -p my-web-app/environments

# 开发环境
cat > my-web-app/environments/dev.yaml << 'EOF'
replicaCount: 1
image:
  tag: latest
resources:
  requests:
    cpu: 50m
    memory: 64Mi
EOF

# 生产环境
cat > my-web-app/environments/prod.yaml << 'EOF'
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: "1"
    memory: "1Gi"
EOF

# 部署到开发环境
helm upgrade --install my-app-dev my-web-app/ \
  -f my-web-app/environments/dev.yaml \
  -n development --create-namespace

# 部署到生产环境
helm upgrade --install my-app-prod my-web-app/ \
  -f my-web-app/environments/prod.yaml \
  -n production --create-namespace
```

### 练习 3：故障排查 — Helm 部署失败

**场景**：`helm install` 或 `helm upgrade` 失败，需要排查原因。

```bash
# 1. 使用 --dry-run 预览
helm upgrade --install my-app mychart/ --dry-run --debug

# 2. 查看 Release 状态
helm status my-app -n production

# 3. 查看 Release 历史
helm history my-app -n production

# 4. 查看失败的 Pod
kubectl get pods -n production | grep -E "Error|CrashLoop|ImagePull"

# 5. 查看 Pod 事件
kubectl describe pod <pod-name> -n production

# 6. 查看 Hook 状态
helm get hooks my-app -n production

# 7. 如果是 Hook 失败，查看 Hook 日志
kubectl logs <hook-pod-name> -n production

# 8. 回滚到上一个成功版本
helm rollback my-app -n production
```

---

## 🎯 面试题精选

### 1. Helm 2 和 Helm 3 的主要区别？

**答**：
- Helm 2 有 Tiller（服务端组件），Helm 3 移除了 Tiller，更安全
- Helm 3 的 Release 信息存储在 namespace 的 Secrets 中（Helm 2 存在 Tiller 中）
- Helm 3 支持 OCI 镜像仓库存储 Chart
- Helm 3 支持 JSON Schema 验证 values
- Helm 3 的 Chart API 版本为 v2（Helm 2 为 v1）
- Helm 3 的依赖管理在 Chart.yaml 中（Helm 2 在 requirements.yaml 中）

### 2. values 文件的优先级顺序？

**答**：优先级从高到低：
1. `--set` 命令行参数
2. `--set-file` / `--set-string` 命令行参数
3. `-f` / `--values` 文件参数（后添加的优先级更高）
4. Chart 中的 `values.yaml`（默认值）

### 3. Helm Hook 有哪些类型？常见的使用场景？

**答**：Hook 类型包括：pre-install、post-install、pre-upgrade、post-upgrade、pre-rollback、post-rollback、pre-delete、post-delete、test。

常见场景：
- `pre-install/pre-upgrade`：数据库迁移
- `post-install`：初始化数据、注册服务
- `test`：健康检查、连接测试
- `pre-delete`：清理资源

### 4. 如何调试 Helm 模板？

**答**：
```bash
# 渲染模板（不安装）
helm template my-release mychart/ -f values.yaml

# 渲染并验证
helm template my-release mychart/ -f values.yaml --validate

# dry-run 安装
helm install my-release mychart/ --dry-run --debug

# 调试特定模板
helm template my-release mychart/ -s templates/deployment.yaml

# 使用 helm-diff 插件
helm diff upgrade my-release mychart/ -f values.yaml
```

### 5. `_helpers.tpl` 文件的作用是什么？

**答**：`_helpers.tpl` 是模板辅助文件，以 `_` 开头的文件不会被渲染为 K8s 资源。它用于定义可复用的模板函数，如：
- `fullname`：生成全限定名称
- `labels`：生成通用标签
- `selectorLabels`：生成选择器标签
- `serviceAccountName`：生成 ServiceAccount 名称

通过 `{{ include "xxx" . }}` 调用这些函数。

### 6. 如何实现 Chart 的多环境管理？

**答**：
1. 基础 `values.yaml` 提供默认值
2. 每个环境一个独立的 values 文件（如 `values-prod.yaml`）
3. 使用 `-f` 参数叠加多个 values 文件
4. 敏感值通过 `--set` 或外部 Secret 管理
5. 使用 `helm diff` 预览变更

### 7. Helm 依赖管理的三种来源？

**答**：
1. **Helm 仓库**：`repository: "https://charts.bitnami.com/bitnami"`
2. **OCI 仓库**：`repository: "oci://registry-1.docker.io/bitnamicharts/postgresql"`
3. **本地目录**：`repository: "file://../common"`

使用 `helm dependency update` 下载依赖到 `charts/` 目录。

### 8. Hook 的删除策略有哪些？

**答**：
- `before-hook-creation`：新 Hook 执行前删除旧的 Hook 资源
- `hook-succeeded`：Hook 成功后删除 Hook 资源
- `hook-failed`：Hook 失败后删除 Hook 资源
- 可以组合使用，如 `before-hook-creation,hook-succeeded`（推荐）

### 9. 如何回滚 Helm Release？

**答**：
```bash
# 查看历史
helm history my-release -n production

# 回滚到上一个版本
helm rollback my-release -n production

# 回滚到指定版本
helm rollback my-release 2 -n production

# 回滚时等待就绪
helm rollback my-release 2 -n production --wait
```

### 10. 生产环境使用 Helm 的最佳实践？

**答**：
1. 使用 `--atomic` 参数，失败时自动回滚
2. 使用 `--wait` 等待 Pod 就绪
3. 配置 JSON Schema 验证 values
4. 使用 `helm diff` 预览变更
5. 敏感值通过 Secret 管理，不放在 values.yaml 中
6. 使用 OCI 仓库存储 Chart
7. 为每个环境维护独立的 values 文件
8. 使用 Hook 管理数据库迁移等生命周期操作

---

## 📚 深入阅读

- [Helm 官方文档](https://helm.sh/docs/)
- [Helm Chart 最佳实践](https://helm.sh/docs/chart_best_practices/)
- [Helm 模板函数](https://helm.sh/docs/chart_template_guide/functions_and_pipelines/)
- [Helm Hook 文档](https://helm.sh/docs/topics/charts_hooks/)
- [Helm JSON Schema 验证](https://helm.sh/docs/topics/charts_schema/)
- [Artifact Hub（Chart 仓库搜索）](https://artifacthub.io/)
- [Bitnami Charts](https://github.com/bitnami/charts)

---

## ✅ 自检清单

- [ ] 能够解释 Helm 的核心概念（Chart、Release、Repository）
- [ ] 能够创建完整的 Chart 目录结构
- [ ] 能够编写 values.yaml 并提供合理的默认值
- [ ] 精通 Go 模板语法（条件、循环、管道、函数）
- [ ] 能够使用 _helpers.tpl 定义可复用的模板函数
- [ ] 能够管理 Helm 仓库（添加、更新、搜索）
- [ ] 能够使用 OCI 仓库存储和分发 Chart
- [ ] 能够进行 Helm 安装、升级、回滚操作
- [ ] 能够配置 Chart 依赖和条件依赖
- [ ] 能够使用 Hook 管理生命周期操作
- [ ] 能够调试 Helm 模板（template、dry-run、diff）
- [ ] 能够为多环境配置不同的 values 文件
