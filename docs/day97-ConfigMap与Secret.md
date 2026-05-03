# Day 97: ConfigMap 与 Secret

> 📅 日期：2026-05-03
> 📖 学习主题：ConfigMap 与 Secret（配置管理, 热更新, Secret 类型, 加密, 挂载方式, 环境变量, 不可变配置）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 91 Kubernetes Pod, Day 95 Kubernetes Service

## 🎯 学习目标

完成 Day 97 的学习后，你应该能够：

1. 深入理解 ConfigMap 和 Secret 的创建方式和使用场景
2. 掌握配置热更新的机制和限制
3. 了解 Secret 的类型和加密方案
4. 能够在生产环境中安全地管理配置和敏感信息
5. 理解不可变配置（Immutable）的性能优势

---

## 📖 核心知识点

### 1. 配置管理概述

#### 1.1 12-Factor App 中的配置原则

```
12-Factor App 原则 III：配置（Config）

配置应该存储在环境变量中，而不是代码中。
配置 = 在不同部署环境之间会变化的任何东西。

示例：
  - 数据库连接字符串
  - API 密钥
  - 缓存服务器地址
  - 功能开关
  - 日志级别

Kubernetes 实现方式：
  ConfigMap  →  非敏感配置
  Secret     →  敏感配置（密码、证书、令牌）
```

#### 1.2 ConfigMap vs Secret 对比

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 数据类型 | 非敏感配置 | 敏感数据 |
| 存储格式 | 明文 | Base64 编码（非加密） |
| etcd 存储 | 明文 | Base64 编码 |
| 大小限制 | 1MB（整个 ConfigMap） | 1MB（整个 Secret） |
| 使用方式 | 环境变量/挂载文件 | 环境变量/挂载文件 |
| 热更新 | 支持（挂载方式） | 支持（挂载方式） |
| 不可变 | 支持 | 支持 |
| 自动更新 | 挂载后约 60-90 秒 | 挂载后约 60-90 秒 |

---

### 2. ConfigMap 详解

#### 2.1 创建 ConfigMap 的四种方式

```yaml
# 方式 1：YAML 声明式
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: default
data:
  # 键值对配置
  APP_ENV: "production"
  LOG_LEVEL: "info"
  MAX_CONNECTIONS: "100"
  # 配置文件
  database.conf: |
    host=db.production.svc.cluster.local
    port=3306
    pool_size=10
    timeout=30
  nginx.conf: |
    server {
        listen 80;
        server_name localhost;
        location / {
            proxy_pass http://backend:8080;
        }
    }
  # 嵌套键（使用 --from-literal 创建时）
  config.json: |
    {
      "database": {
        "host": "db.production.svc.cluster.local",
        "port": 3306
      },
      "cache": {
        "redis": "redis.production.svc.cluster.local:6379"
      }
    }
```

```bash
# 方式 2：从键值对创建
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100

# 方式 3：从文件创建
kubectl create configmap app-config \
  --from-file=database.conf=./config/database.conf \
  --from-file=nginx.conf=./config/nginx.conf

# 方式 4：从目录创建（目录下每个文件成为一个键）
kubectl create configmap app-config --from-file=./config/
```

#### 2.2 使用 ConfigMap：环境变量

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-config
spec:
  containers:
    - name: app
      image: myapp:1.0
      env:
        # 方式 1：单个键值对
        - name: APP_ENV
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_ENV
              optional: false    # 如果 ConfigMap 不存在，Pod 启动失败
        # 方式 2：引用整个 ConfigMap
        # 所有键值对都成为环境变量
      envFrom:
        - configMapRef:
            name: app-config
            optional: true       # ConfigMap 不存在时不影响 Pod 启动
        # 添加前缀
        - configMapRef:
            name: database-config
          prefix: DB_            # 键名变为 DB_HOST, DB_PORT 等
```

#### 2.3 使用 ConfigMap：挂载文件

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-volume
spec:
  containers:
    - name: app
      image: myapp:1.0
      volumeMounts:
        # 方式 1：挂载整个 ConfigMap 为目录
        - name: config-volume
          mountPath: /etc/config
          readOnly: true
        # 方式 2：挂载单个键为文件
        - name: config-volume
          mountPath: /etc/nginx/nginx.conf
          subPath: nginx.conf    # 只挂载 nginx.conf 这一个键
          readOnly: true
      # subPath 的重要区别：
      # 不使用 subPath：整个目录被挂载，支持热更新
      # 使用 subPath：只挂载指定文件，不支持热更新
  volumes:
    - name: config-volume
      configMap:
        name: app-config
        # 可选：指定挂载的键
        items:
          - key: database.conf
            path: database.conf    # 文件名
            mode: 0644             # 文件权限
          - key: nginx.conf
            path: nginx.conf
            mode: 0644
```

#### 2.4 ConfigMap 热更新机制（SRE 重点）

```
┌─ ConfigMap 热更新流程 ──────────────────────────────────┐
│                                                         │
│  1. 修改 ConfigMap                                      │
│     kubectl edit configmap app-config                   │
│     或 kubectl apply -f configmap-new.yaml              │
│                                                         │
│  2. kubelet 检测到变化（Sync Period）                   │
│     - 默认每 60-90 秒检查一次                           │
│     - 通过 watch 机制感知变化                           │
│                                                         │
│  3. 更新挂载的文件                                      │
│     - 更新 volume 中的符号链接                          │
│     - 指向新的 ConfigMap 数据                           │
│                                                         │
│  4. 应用读取到新配置                                    │
│     - 应用需要重新读取文件                              │
│     - 大多数应用不会自动重新加载                        │
│                                                         │
│  重要限制：                                             │
│  - 使用 subPath 挂载时不支持热更新                      │
│  - 环境变量方式不支持热更新（需要重启 Pod）             │
│  - 应用需要自行监听文件变化或定期重读                   │
│  - 更新延迟约 60-90 秒（kubelet sync period）           │
└─────────────────────────────────────────────────────────┘
```

```bash
# 验证热更新
# 1. 创建 ConfigMap
kubectl create configmap test-config --from-literal=data=version1

# 2. 创建 Pod 挂载 ConfigMap
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: config-watcher
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "while true; do cat /etc/config/data; echo; sleep 5; done"]
      volumeMounts:
        - name: config
          mountPath: /etc/config
  volumes:
    - name: config
      configMap:
        name: test-config
EOF

# 3. 观察输出
kubectl logs -f config-watcher

# 4. 修改 ConfigMap
kubectl edit configmap test-config  # 将 data 改为 version2

# 5. 等待 60-90 秒，观察日志变化
# 输出应该从 version1 变为 version2
```

#### 2.5 应用程序如何感知配置变化

```python
# Python 示例：监听配置文件变化
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.conf'):
            print(f"Config changed: {event.src_path}")
            reload_config()

def reload_config():
    with open('/etc/config/database.conf') as f:
        config = parse_config(f.read())
        # 重新初始化连接池等
        update_connection_pool(config)

if __name__ == "__main__":
    path = '/etc/config'
    observer = Observer()
    observer.schedule(ConfigHandler(), path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

```go
// Go 示例：使用 fsnotify 监听文件变化
package main

import (
    "log"
    "github.com/fsnotify/fsnotify"
)

func main() {
    watcher, _ := fsnotify.NewWatcher()
    defer watcher.Close()

    done := make(chan bool)
    go func() {
        for {
            select {
            case event, ok := <-watcher.Events:
                if !ok { return }
                if event.Op&fsnotify.Write == fsnotify.Write {
                    log.Println("Config file modified:", event.Name)
                    reloadConfig()
                }
            case err, ok := <-watcher.Errors:
                if !ok { return }
                log.Println("Error:", err)
            }
        }
    }()

    watcher.Add("/etc/config/database.conf")
    <-done
}

func reloadConfig() {
    // 重新读取配置文件
    // 更新应用状态
}
```

---

### 3. Secret 详解

#### 3.1 Secret 类型

| 类型 | 用途 | data 字段 |
|------|------|-----------|
| Opaque | 通用 Secret | 用户自定义 |
| kubernetes.io/tls | TLS 证书 | tls.crt, tls.key |
| kubernetes.io/dockerconfigjson | Docker 仓库认证 | .dockerconfigjson |
| kubernetes.io/basic-auth | 基本认证 | username, password |
| kubernetes.io/ssh-auth | SSH 认证 | ssh-privatekey |
| kubernetes.io/service-account-token | SA 令牌 | token, ca.crt, namespace |
| kubernetes.io/bootstrap.token | 引导令牌 | token-id, token-secret |

#### 3.2 创建 Secret

```bash
# 方式 1：从字面量创建
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password='S3cr3tP@ssw0rd!'

# 方式 2：从文件创建
kubectl create secret generic tls-secret \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key

# 方式 3：从环境文件创建
echo -n 'admin' > ./username.txt
echo -n 'S3cr3tP@ssw0rd!' > ./password.txt
kubectl create secret generic db-credentials \
  --from-file=./username.txt \
  --from-file=./password.txt

# 方式 4：创建 Docker Registry Secret
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=admin \
  --docker-password='D0ckerP@ss!' \
  --docker-email=admin@example.com

# 方式 5：创建 TLS Secret
kubectl create secret tls my-tls --cert=server.crt --key=server.key
```

```yaml
# 方式 6：YAML 声明式
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
# data 字段：Base64 编码的值
data:
  username: YWRtaW4=              # echo -n 'admin' | base64
  password: UzNjcjN0UEBzc3cwcmQh  # echo -n 'S3cr3tP@ssw0rd!' | base64
# stringData 字段：明文值（创建时自动编码）
stringData:
  username: admin
  password: 'S3cr3tP@ssw0rd!'
```

#### 3.3 使用 Secret：环境变量

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-secret
spec:
  containers:
    - name: app
      image: myapp:1.0
      env:
        # 单个键引用
        - name: DB_USERNAME
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: username
              optional: false
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
      # 引用整个 Secret
      envFrom:
        - secretRef:
            name: db-credentials
          prefix: SECRET_          # 键名变为 SECRET_username, SECRET_password
```

#### 3.4 使用 Secret：挂载文件

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-tls
spec:
  containers:
    - name: app
      image: nginx:1.25
      volumeMounts:
        - name: tls-certs
          mountPath: /etc/tls
          readOnly: true
        - name: docker-config
          mountPath: /root/.docker
          readOnly: true
  volumes:
    # TLS 证书
    - name: tls-certs
      secret:
        secretName: my-tls
        defaultMode: 0400        # 只读权限
        items:
          - key: tls.crt
            path: server.crt
          - key: tls.key
            path: server.key
    # Docker 配置
    - name: docker-config
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: config.json
```

#### 3.5 Secret 用于 Image Pull

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: private-image-pod
spec:
  containers:
    - name: app
      image: registry.example.com/myapp:1.0
  imagePullSecrets:
    - name: regcred    # Docker Registry Secret
```

---

### 4. Secret 加密与安全

#### 4.1 Base64 不是加密

```
常见误解：Secret 的 data 字段使用 Base64 编码，很多人误以为这是加密。

事实：
  Base64 只是编码，不是加密！
  任何人都可以轻松解码：echo 'UzNjcjN0UEBzc3cwcmQh' | base64 -d

  etcd 中存储的 Secret 是 Base64 编码的明文
  任何有 etcd 读权限的人都能看到原始值

真正的安全措施：
  1. etcd 加密（EncryptionConfiguration）
  2. RBAC 权限控制
  3. 外部密钥管理（Vault、AWS Secrets Manager）
  4. 审计日志
```

#### 4.2 etcd 加密配置（EncryptionConfiguration）

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
      - configmaps
    providers:
      # 首先尝试 aescbc（强加密）
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>  # head -c 32 /dev/urandom | base64
      # 回退到 secretbox
      - secretbox:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      # 最后回退到 identity（不加密，用于读取旧数据）
      - identity: {}
```

```bash
# 生成加密密钥
head -c 32 /dev/urandom | base64

# 启用加密（kube-apiserver 启动参数）
--encryption-provider-config=/etc/kubernetes/encryption-config.yaml

# 加密已有的 Secret
kubectl get secrets --all-namespaces -o json | kubectl replace -f -

# 验证加密
ETCDCTL_API=3 etcdctl get /registry/secrets/default/db-credentials --print-value-only | hexdump -C
# 应该看到加密后的数据，而不是 Base64 编码的明文
```

#### 4.3 外部密钥管理：HashiCorp Vault

```yaml
# 使用 Vault CSI Driver 注入 Secret
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: vault-db-credentials
spec:
  provider: vault
  parameters:
    roleName: "myapp"
    vaultAddress: "https://vault.example.com:8200"
    objects: |
      - objectName: "username"
        secretPath: "secret/data/myapp/db"
        secretKey: "username"
      - objectName: "password"
        secretPath: "secret/data/myapp/db"
        secretKey: "password"
  # 可选：同步为 Kubernetes Secret
  secretObjects:
    - secretName: db-credentials-synced
      type: Opaque
      data:
        - objectName: username
          key: username
        - objectName: password
          key: password
---
apiVersion: v1
kind: Pod
metadata:
  name: app-with-vault
spec:
  serviceAccountName: myapp
  containers:
    - name: app
      image: myapp:1.0
      volumeMounts:
        - name: secrets
          mountPath: "/mnt/secrets"
          readOnly: true
  volumes:
    - name: secrets
      csi:
        driver: secrets-store.csi.k8s.io
        readOnly: true
        volumeAttributes:
          secretProviderClass: "vault-db-credentials"
```

#### 4.4 AWS Secrets Manager 集成

```yaml
# 使用 External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h          # 同步间隔
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials-k8s   # 创建的 K8s Secret 名称
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: production/myapp/db    # AWS Secrets Manager 中的路径
        property: username
    - secretKey: password
      remoteRef:
        key: production/myapp/db
        property: password
---
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

---

### 5. 不可变 ConfigMap 和 Secret（Immutable）

#### 5.1 为什么使用不可变配置

```
普通 ConfigMap/Secret 的问题：
  1. kubelet 需要定期 watch 所有挂载的 ConfigMap/Secret
  2. 大规模集群中，数千个 ConfigMap 的 watch 对 API Server 压力很大
  3. 配置变更需要传播到所有使用节点

不可变配置的优势：
  1. 减少 API Server 负载（不需要 watch）
  2. 防止意外修改（保护关键配置）
  3. 提高集群性能（大规模集群效果显著）
  4. 配置版本化（每次变更创建新版本）
```

#### 5.2 配置不可变 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-v1    # 使用版本号命名
immutable: true           # 关键字段：设为不可变
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
```

#### 5.3 不可变配置的工作流

```
┌─ 不可变配置工作流 ──────────────────────────────────────┐
│                                                         │
│  1. 创建配置版本 v1                                     │
│     app-config-v1 (immutable: true)                     │
│     Deployment 挂载 app-config-v1                       │
│                                                         │
│  2. 需要更新配置                                        │
│     创建 app-config-v2 (immutable: true)                │
│     更新 Deployment 引用 app-config-v2                  │
│     触发滚动更新                                        │
│                                                         │
│  3. 回滚                                                │
│     将 Deployment 改回 app-config-v1                    │
│     触发滚动更新                                        │
│                                                         │
│  4. 清理旧版本                                          │
│     确认没有 Pod 使用 app-config-v1 后删除              │
│                                                         │
│  优势：                                                 │
│  + 配置版本化，可追溯                                   │
│  + 回滚简单，只需改引用                                 │
│  + 减少 API Server 负载                                 │
│  + 防止意外修改                                         │
└─────────────────────────────────────────────────────────┘
```

#### 5.4 版本化配置的 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
      annotations:
        config-version: "v2"    # 记录配置版本，便于追踪
    spec:
      containers:
        - name: app
          image: myapp:1.0
          envFrom:
            - configMapRef:
                name: app-config-v2    # 引用特定版本
          volumeMounts:
            - name: config
              mountPath: /etc/config
      volumes:
        - name: config
          configMap:
            name: app-config-v2
```

---

### 6. 配置管理最佳实践

#### 6.1 配置分层策略

```
┌─ 配置分层 ──────────────────────────────────────────────┐
│                                                         │
│  层级 1：基础设施配置（集群级别）                        │
│    - CoreDNS 配置                                       │
│    - kube-proxy 配置                                    │
│    - Ingress Controller 配置                            │
│    管理方式：集群运维团队管理                            │
│                                                         │
│  层级 2：环境配置（命名空间级别）                        │
│    - 数据库连接信息                                     │
│    - 缓存服务器地址                                     │
│    - 外部服务端点                                       │
│    管理方式：环境运维团队管理                            │
│                                                         │
│  层级 3：应用配置（Deployment 级别）                     │
│    - 日志级别                                           │
│    - 功能开关                                           │
│    - 业务参数                                           │
│    管理方式：应用开发团队管理                            │
│                                                         │
│  层级 4：敏感配置（Secret 级别）                         │
│    - 密码、密钥                                         │
│    - 证书                                               │
│    - API 令牌                                           │
│    管理方式：安全团队 + 外部密钥管理                     │
└─────────────────────────────────────────────────────────┘
```

#### 6.2 配置命名规范

```yaml
# 命名规范：<app>-<config-type>-<version>
# 示例：
app-config-v1              # 应用配置
app-db-credentials-v1      # 数据库凭证
app-tls-certs-v1           # TLS 证书
app-feature-flags-v1       # 功能开关

# 标签规范
metadata:
  name: myapp-config-v2
  labels:
    app: myapp
    config-type: application
    version: "v2"
    managed-by: helm          # 或 kustomize, argocd
```

#### 6.3 Kustomize 管理配置

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

configMapGenerator:
  - name: app-config
    behavior: merge            # merge/create/replace
    literals:
      - APP_ENV=production
      - LOG_LEVEL=info
    files:
      - configs/database.conf
      - configs/nginx.conf

secretGenerator:
  - name: db-credentials
    type: Opaque
    literals:
      - username=admin
      - password=S3cr3tP@ss!
    options:
      disableNameSuffixHash: false    # 自动生成名称后缀

# 环境覆盖
patchesStrategicMerge:
  - overlays/production/config-patch.yaml
```

---

### 7. SRE 实战：配置管理故障排查

#### 7.1 常见问题清单

```
问题 1：Pod 启动失败 - ConfigMap/Secret 不存在
  → 检查 ConfigMap/Secret 是否在同命名空间
  → 检查名称拼写
  → 检查 optional 字段设置

问题 2：配置更新后 Pod 未生效
  → 环境变量方式：需要重启 Pod
  → subPath 挂载：不支持热更新
  → 普通挂载：等待 60-90 秒
  → 应用未重新读取配置文件

问题 3：Secret 值不正确
  → 检查 Base64 编码是否正确
  → echo -n 'value' | base64（注意 -n 参数）
  → 检查 stringData 和 data 字段

问题 4：配置文件权限问题
  → 检查 defaultMode 设置
  → Secret 默认权限 0644（可能需要 0400）
  → 检查 runAsUser 和 fsGroup

问题 5：不可变配置无法修改
  → 不可变 ConfigMap/Secret 创建后不能修改
  → 必须创建新版本
  → 更新 Deployment 引用新版本
```

#### 7.2 排查命令

```bash
# 1. 检查 ConfigMap
kubectl get configmap <name> -o yaml
kubectl describe configmap <name>

# 2. 检查 Secret（Base64 编码）
kubectl get secret <name> -o yaml
kubectl describe secret <name>

# 3. 解码 Secret 值
kubectl get secret <name> -o jsonpath='{.data.username}' | base64 -d
kubectl get secret <name> -o jsonpath='{.data.password}' | base64 -d

# 4. 检查 Pod 的环境变量
kubectl exec <pod> -- env | grep <prefix>

# 5. 检查挂载的文件
kubectl exec <pod> -- ls -la /etc/config/
kubectl exec <pod> -- cat /etc/config/database.conf

# 6. 检查文件权限
kubectl exec <pod> -- stat /etc/config/database.conf

# 7. 检查热更新状态
kubectl exec <pod> -- cat /etc/config/..data    # 查看符号链接
```

---

## 💻 实战练习

### 练习 1：ConfigMap 热更新实验

**目标**：验证 ConfigMap 热更新机制

```bash
# 1. 创建初始 ConfigMap
kubectl create configmap app-settings --from-literal=log_level=info --from-literal=max_retries=3

# 2. 创建使用 ConfigMap 的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: config-test
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "while true; do echo '=== Config Content ==='; cat /etc/app/log_level; cat /etc/app/max_retries; echo '=== End ==='; sleep 10; done"]
      volumeMounts:
        - name: config
          mountPath: /etc/app
  volumes:
    - name: config
      configMap:
        name: app-settings
EOF

# 3. 观察初始输出
kubectl logs -f config-test

# 4. 在另一个终端修改 ConfigMap
kubectl edit configmap app-settings
# 将 log_level 改为 debug，max_retries 改为 5

# 5. 等待 60-90 秒，观察输出变化

# 6. 验证 subPath 不支持热更新
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: config-subpath-test
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "while true; do cat /etc/app/log_level; echo; sleep 10; done"]
      volumeMounts:
        - name: config
          mountPath: /etc/app/log_level
          subPath: log_level
  volumes:
    - name: config
      configMap:
        name: app-settings
EOF

# 7. 修改 ConfigMap，观察 subPath 挂载的文件不会变化
```

### 练习 2：Secret 安全管理

**目标**：实践 Secret 的创建、使用和安全配置

```bash
# 1. 创建多种类型的 Secret
# 通用 Secret
kubectl create secret generic app-secrets \
  --from-literal=api_key=sk-1234567890abcdef \
  --from-literal=db_password='MyS3cr3tP@ss!'

# TLS Secret
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=myapp.local"
kubectl create secret tls myapp-tls --cert=tls.crt --key=tls.key

# 2. 查看 Secret
kubectl get secrets
kubectl describe secret app-secrets
kubectl get secret app-secrets -o yaml

# 3. 解码 Secret
echo "API Key:"
kubectl get secret app-secrets -o jsonpath='{.data.api_key}' | base64 -d
echo
echo "DB Password:"
kubectl get secret app-secrets -o jsonpath='{.data.db_password}' | base64 -d
echo

# 4. 在 Pod 中使用 Secret（环境变量）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-env-test
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "env | grep -E 'API_KEY|DB_PASSWORD'; sleep 3600"]
      env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: api_key
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: db_password
EOF

# 5. 在 Pod 中使用 Secret（挂载文件）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-file-test
spec:
  containers:
    - name: busybox
      image: busybox:1.36
      command: ["sh", "-c", "ls -la /etc/secrets/; cat /etc/secrets/api_key; sleep 3600"]
      volumeMounts:
        - name: secrets
          mountPath: /etc/secrets
          readOnly: true
  volumes:
    - name: secrets
      secret:
        secretName: app-secrets
        defaultMode: 0400    # 只读权限
EOF

# 6. 验证文件权限
kubectl exec secret-file-test -- ls -la /etc/secrets/

# 7. 清理
kubectl delete pod secret-env-test secret-file-test
kubectl delete secret app-secrets myapp-tls
rm -f tls.key tls.crt
```

### 练习 3：不可变配置实践

**目标**：实践不可变配置的版本管理

```bash
# 1. 创建不可变 ConfigMap v1
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-v1
immutable: true
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  FEATURE_NEW_UI: "false"
EOF

# 2. 创建使用 v1 配置的 Deployment
kubectl create deployment config-app --image=nginx --replicas=2
kubectl set env deployment/config-app --from=configmap/app-config-v1

# 3. 验证配置
kubectl exec deploy/config-app -- env | grep -E 'APP_ENV|LOG_LEVEL|FEATURE_NEW_UI'

# 4. 尝试修改不可变 ConfigMap（会失败）
kubectl edit configmap app-config-v1
# 错误：configmaps "app-config-v1" is immutable

# 5. 创建 v2 版本
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-v2
immutable: true
data:
  APP_ENV: "production"
  LOG_LEVEL: "debug"
  FEATURE_NEW_UI: "true"
EOF

# 6. 更新 Deployment 使用 v2
kubectl set env deployment/config-app --from=configmap/app-config-v2

# 7. 验证滚动更新
kubectl rollout status deployment/config-app
kubectl exec deploy/config-app -- env | grep -E 'APP_ENV|LOG_LEVEL|FEATURE_NEW_UI'

# 8. 回滚到 v1
kubectl set env deployment/config-app --from=configmap/app-config-v1
kubectl rollout status deployment/config-app

# 9. 清理
kubectl delete deployment config-app
kubectl delete configmap app-config-v1 app-config-v2
```

---

## 🎯 面试题精选

### 题目 1：ConfigMap 和 Secret 有什么区别？

**参考答案**：

- **ConfigMap**：用于存储非敏感的配置数据，以明文形式存储在 etcd 中。
- **Secret**：用于存储敏感数据（密码、密钥、证书），以 Base64 编码存储在 etcd 中。

关键区别：
1. Secret 支持 `type` 字段（如 `kubernetes.io/tls`、`kubernetes.io/dockerconfigjson`）
2. Secret 的 Base64 编码不是加密，需要额外的加密措施（EncryptionConfiguration、Vault）
3. Secret 在 Pod 中挂载时默认权限为 0644，建议设置为 0400
4. 两者都可以通过环境变量或文件挂载方式使用

### 题目 2：ConfigMap 的热更新机制是怎样的？有什么限制？

**参考答案**：

热更新机制：
1. 修改 ConfigMap 后，kubelet 通过 watch 机制感知变化
2. kubelet 更新挂载卷中的符号链接，指向新的 ConfigMap 数据
3. 更新延迟约 60-90 秒（kubelet sync period）

限制：
1. **环境变量方式不支持热更新**：环境变量在 Pod 启动时注入，后续不会变化
2. **subPath 挂载不支持热更新**：subPath 方式挂载的文件不会自动更新
3. **应用需要自行重读配置**：大多数应用不会自动感知文件变化
4. **更新延迟**：约 60-90 秒

### 题目 3：什么是不可变 ConfigMap/Secret？为什么使用它？

**参考答案**：

不可变配置是 Kubernetes 1.21+ 的特性，通过设置 `immutable: true` 使 ConfigMap/Secret 创建后不能修改。

优势：
1. **减少 API Server 负载**：kubelet 不需要 watch 不可变配置
2. **防止意外修改**：保护关键配置不被误改
3. **配置版本化**：每次变更创建新版本，便于追溯和回滚
4. **大规模集群性能优化**：显著减少 API Server 的 watch 数量

使用场景：
- 生产环境的数据库配置
- 应用的核心配置
- 需要版本管理的配置

### 题目 4：Secret 的 Base64 编码是加密吗？如何真正加密 Secret？

**参考答案**：

**不是加密**。Base64 只是编码，任何人都可以轻松解码。etcd 中存储的 Secret 是 Base64 编码的明文。

真正的加密方式：
1. **etcd EncryptionConfiguration**：在 API Server 层面加密，使用 aescbc 或 secretbox 加密
2. **HashiCorp Vault**：外部密钥管理，通过 CSI Driver 或 Sidecar 注入
3. **AWS Secrets Manager / GCP Secret Manager**：云厂商密钥管理服务
4. **Sealed Secrets**：将 Secret 加密为 SealedSecret 资源，只能在特定集群解密

### 题目 5：如何在 Pod 中使用私有镜像仓库的镜像？

**参考答案**：

1. 创建 Docker Registry Secret：
```bash
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=admin \
  --docker-password=password
```

2. 在 Pod 中引用：
```yaml
spec:
  imagePullSecrets:
    - name: regcred
  containers:
    - name: app
      image: registry.example.com/myapp:1.0
```

### 题目 6：ConfigMap 的大小限制是多少？超过限制怎么办？

**参考答案**：

ConfigMap 的大小限制是 **1MB**（整个 ConfigMap 对象）。

超过限制的解决方案：
1. **拆分 ConfigMap**：将大配置拆分为多个 ConfigMap
2. **使用 PV/NFS**：将配置文件存储在持久卷中
3. **配置中心**：使用 Consul、Apollo、Nacos 等外部配置中心
4. **Init Container**：使用 Init Container 从外部拉取配置

### 题目 7：如何实现配置的灰度发布？

**参考答案**：

1. **多版本 ConfigMap**：
   - 创建 app-config-v1（当前版本）
   - 创建 app-config-v2（新版本）
   - 部分 Deployment 引用 v2，部分引用 v1
   - 观察无问题后，全部切换到 v2

2. **使用 Helm/Kustomize**：
   - 通过 Helm values 或 Kustomize overlay 管理不同环境的配置

3. **使用 ArgoCD**：
   - 通过 ArgoCD ApplicationSet 管理多环境配置

### 题目 8：Secret 挂载到 Pod 中的默认权限是什么？如何修改？

**参考答案**：

默认权限：**0644**（rw-r--r--），即所有者可读写，其他人可读。

修改方式：
```yaml
volumes:
  - name: secrets
    secret:
      secretName: my-secret
      defaultMode: 0400    # 只读权限（rw-------）
```

安全建议：
- 敏感配置（如私钥）设置为 0400
- 非敏感配置可保持 0644
- 使用 `fsGroup` 确保 Pod 用户可以读取

### 题目 9：如何从文件创建 ConfigMap？

**参考答案**：

```bash
# 单个文件
kubectl create configmap app-config --from-file=config.yaml

# 多个文件
kubectl create configmap app-config \
  --from-file=config1.yaml \
  --from-file=config2.yaml

# 整个目录
kubectl create configmap app-config --from-file=./config/

# 指定键名
kubectl create configmap app-config --from-file=mykey=./config.yaml
```

### 题目 10：ConfigMap/Secret 更新后，Pod 中的文件如何变化？

**参考答案**：

更新后，kubelet 会更新挂载目录下的符号链接：

```
/etc/config/
├── ..data -> ..<timestamp>    # 符号链接指向当前版本
├── ..2026_05_03_10_00_00/     # 旧版本
│   ├── config1.yaml
│   └── config2.yaml
├── ..2026_05_03_11_00_00/     # 新版本
│   ├── config1.yaml
│   └── config2.yaml
├── config1.yaml -> ..data/config1.yaml
└── config2.yaml -> ..data/config2.yaml
```

应用读取文件时，会读取到符号链接指向的最新版本。

---

## 📚 深入阅读

- [ConfigMap 官方文档](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secret 官方文档](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Kubernetes Secret 加密](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
- [HashiCorp Vault 集成](https://developer.hashicorp.com/vault/docs/platform/k8s)
- [External Secrets Operator](https://external-secrets.io/)
- [Kustomize 文档](https://kustomize.io/)

---

## ✅ 自检清单

- [ ] 能够创建 ConfigMap 和 Secret（YAML、命令行）
- [ ] 理解环境变量和文件挂载两种使用方式的区别
- [ ] 掌握 ConfigMap 热更新的机制和限制
- [ ] 知道 Secret 的 Base64 编码不是加密
- [ ] 了解 etcd 加密和外部密钥管理方案
- [ ] 理解不可变配置的优势和使用场景
- [ ] 能够排查配置相关的常见问题
- [ ] 知道如何实现配置的版本管理
- [ ] 了解 Kustomize 配置管理
