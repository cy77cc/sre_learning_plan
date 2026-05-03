# Day 85: Docker 私有仓库

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 私有仓库
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 77 (Docker 镜像基础), Day 78 (Dockerfile 进阶构建), Day 83 (Dockerfile 最佳实践), Day 81 (Docker 网络管理)

## 🎯 学习目标

- 理解为什么企业需要私有镜像仓库
- 掌握 Docker Registry v2 的部署、配置与管理
- 掌握 Harbor 企业级私有仓库的安装与核心功能
- 能配置 TLS 加密和认证机制
- 理解镜像推送/拉取的完整流程
- 掌握垃圾回收和高可用方案

---

## 📖 核心知识点

### 1. 私有仓库概述

#### 1.1 为什么需要私有仓库

```
公有仓库 (Docker Hub) vs 私有仓库:

┌─────────────────────┬────────────────────────────────────┐
│     Docker Hub      │        私有仓库                    │
├─────────────────────┼────────────────────────────────────┤
│ 镜像存储在公网       │ 镜像存储在企业内网                  │
│ 免费有限额           │ 无限制                             │
│ 公开镜像可被任何人拉取│ 完全受控的访问权限                  │
│ 网络延迟取决于公网   │ 内网拉取速度极快                    │
│ 无企业审计功能       │ 完整的审计日志                      │
│ 无漏洞扫描集成       │ 集成 Trivy/Clair 漏洞扫描           │
│ 无镜像复制          │ 支持跨数据中心镜像复制               │
│ 无 RBAC            │ 完整的角色权限管理                   │
└─────────────────────┴────────────────────────────────────┘

企业私有仓库的核心价值:
1. 安全: 镜像不暴露在公网，降低供应链攻击风险
2. 合规: 满足数据驻留、审计等合规要求
3. 性能: 内网传输速度远高于公网
4. 控制: 自主管理镜像生命周期、访问权限
5. 集成: 与 CI/CD、漏洞扫描、签名验证深度集成
```

#### 1.2 私有仓库方案对比

| 方案 | 类型 | 适用规模 | 核心功能 | 复杂度 |
|------|------|---------|---------|--------|
| Docker Registry v2 | 基础 | 小团队/开发 | 镜像存储、推送/拉取 | 低 |
| Harbor | 企业级 | 中大型企业 | RBAC、扫描、复制、GC、UI | 中 |
| AWS ECR | 云托管 | AWS 用户 | 托管、IAM 集成 | 低 |
| GitHub GHCR | 云托管 | GitHub 用户 | Actions 集成 | 低 |
| Nexus | 通用制品 | DevOps 团队 | 多格式制品管理 | 中 |
| GitLab Registry | 集成 | GitLab 用户 | CI/CD 集成 | 低 |

---

### 2. Docker Registry v2

#### 2.1 Registry v2 架构

```
Docker Registry v2 架构:

┌──────────────────────────────────────────────────┐
│                  Docker Client                    │
│  docker push / docker pull                        │
└──────────────┬───────────────────────────────────┘
               │ HTTP/HTTPS
               ▼
┌──────────────────────────────────────────────────┐
│              Registry v2 API                      │
│  /v2/                                            │
│  ├── /v2/<name>/manifests/<reference>            │
│  ├── /v2/<name>/blobs/<digest>                   │
│  └── /v2/_catalog                                │
├──────────────────────────────────────────────────┤
│              Registry 存储后端                     │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  local      │  │  S3/GCS     │  │  Swift   │ │
│  │  filesystem │  │  Azure Blob │  │  OSS     │ │
│  └─────────────┘  └─────────────┘  └──────────┘ │
│                                                  │
│  存储结构:                                        │
│  /var/lib/registry/                              │
│  └── docker/registry/v2/                         │
│      ├── blobs/        # 层数据 (content-addressable)│
│      │   └── sha256/                           │
│      │       ├── ab/                            │
│      │       │   └── abcdef1234.../             │
│      │       │       └── data                   │
│      │       └── cd/                            │
│      └── repositories/ # 镜像元数据              │
│          └── myapp/                             │
│              ├── _manifests/                    │
│              │   ├── revisions/sha256/          │
│              │   └── tags/                      │
│              │       └── v1/                    │
│              └── _layers/sha256/                │
└──────────────────────────────────────────────────┘
```

#### 2.2 部署基础 Registry

```bash
# === 最简单的部署 ===
docker run -d --name registry \
    -p 5000:5000 \
    --restart unless-stopped \
    registry:2

# === 带数据持久化的部署 ===
docker run -d --name registry \
    -p 5000:5000 \
    -v /opt/registry/data:/var/lib/registry \
    --restart unless-stopped \
    registry:2

# === 带自定义配置的部署 ===
mkdir -p /opt/registry/{data,config}

cat > /opt/registry/config/config.yml << 'EOF'
version: 0.1
log:
  fields:
    service: registry
  level: info
  formatter: text
storage:
  filesystem:
    rootdirectory: /var/lib/registry
    maxthreads: 100
  cache:
    blobdescriptor: inmemory
  delete:
    enabled: true
  maintenance:
    uploadpurging:
      enabled: true
      age: 168h      # 7 天后清理未完成的上传
      interval: 24h
      dryrun: false
http:
  addr: :5000
  headers:
    X-Content-Type-Options: [nosniff]
  draintimeout: 60s
health:
  storagedriver:
    enabled: true
    interval: 10s
    threshold: 3
EOF

docker run -d --name registry \
    -p 5000:5000 \
    -v /opt/registry/data:/var/lib/registry \
    -v /opt/registry/config/config.yml:/etc/docker/registry/config.yml:ro \
    --restart unless-stopped \
    registry:2
```

#### 2.3 镜像推送与拉取

```bash
# === 推送镜像到私有仓库 ===

# 1. 给镜像打标签
docker tag myapp:latest localhost:5000/myapp:v1
docker tag myapp:latest localhost:5000/myapp:latest
docker tag myapp:latest registry.example.com:5000/myapp:v1

# 2. 推送镜像
docker push localhost:5000/myapp:v1
docker push localhost:5000/myapp:latest

# 3. 拉取镜像
docker pull localhost:5000/myapp:v1

# === 查看仓库中的镜像 ===
# 使用 API 查看 catalog
curl http://localhost:5000/v2/_catalog
# {"repositories":["myapp"]}

# 查看镜像的 tags
curl http://localhost:5000/v2/myapp/tags/list
# {"name":"myapp","tags":["v1","latest"]}

# 查看 manifest (镜像详情)
curl -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    http://localhost:5000/v2/myapp/manifests/v1

# === 删除镜像 ===
# 先获取 digest
DIGEST=$(curl -s -I -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    http://localhost:5000/v2/myapp/manifests/v1 | grep Docker-Content-Digest | awk '{print $2}' | tr -d '\r')

# 删除
curl -X DELETE http://localhost:5000/v2/myapp/manifests/$DIGEST

# 运行垃圾回收回收空间
docker exec registry bin/registry garbage-collect /etc/docker/registry/config.yml
```

#### 2.4 Registry TLS 配置

```bash
# === 自签名证书 ===

# 创建证书目录
mkdir -p /opt/registry/{certs,config,data}

# 生成 CA 证书
openssl genrsa -out /opt/registry/certs/ca.key 4096
openssl req -x509 -new -nodes -sha512 -days 3650 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=MyOrg/CN=RegistryCA" \
    -key /opt/registry/certs/ca.key \
    -out /opt/registry/certs/ca.crt

# 生成服务器证书
openssl genrsa -out /opt/registry/certs/registry.key 4096
openssl req -sha512 -new \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=MyOrg/CN=registry.example.com" \
    -key /opt/registry/certs/registry.key \
    -out /opt/registry/certs/registry.csr

# 创建 SAN 扩展文件
cat > /opt/registry/certs/extfile.cnf << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1=registry.example.com
DNS.2=registry
IP.1=127.0.0.1
IP.2=10.0.1.100
EOF

openssl x509 -req -sha512 -days 3650 \
    -extfile /opt/registry/certs/extfile.cnf \
    -CA /opt/registry/certs/ca.crt \
    -CAkey /opt/registry/certs/ca.key \
    -CAcreateserial \
    -in /opt/registry/certs/registry.csr \
    -out /opt/registry/certs/registry.crt

# === 带 TLS 的 Registry ===
docker run -d --name registry \
    -p 443:443 \
    -v /opt/registry/data:/var/lib/registry \
    -v /opt/registry/certs:/certs:ro \
    -v /opt/registry/config/config.yml:/etc/docker/registry/config.yml:ro \
    -e REGISTRY_HTTP_ADDR=0.0.0.0:443 \
    -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/registry.crt \
    -e REGISTRY_HTTP_TLS_KEY=/certs/registry.key \
    --restart unless-stopped \
    registry:2

# === 配置 Docker 客户端信任自签名证书 ===

# 方式 1: 作为系统 CA 信任 (推荐)
sudo mkdir -p /etc/docker/certs.d/registry.example.com
sudo cp /opt/registry/certs/ca.crt /etc/docker/certs.d/registry.example.com/ca.crt
sudo systemctl restart docker

# 方式 2: insecure-registries (不推荐, 仅开发环境)
# /etc/docker/daemon.json
{
    "insecure-registries": ["registry.example.com"]
}

# 验证
docker login registry.example.com
docker push registry.example.com/myapp:v1
```

```
Registry TLS 配置流程:

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  生成 CA 证书 │────▶│ 生成服务器证书│────▶│ 配置 SAN 扩展│
│  ca.key      │     │ registry.key │     │ DNS/IP 列表  │
│  ca.crt      │     │ registry.crt │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  客户端配置   │◀────│ 启动 Registry│◀────│ 部署证书      │
│  ca.crt 到   │     │ TLS 参数     │     │ 到 /certs    │
│  /etc/docker │     │              │     │              │
│  /certs.d/   │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

#### 2.5 Registry 认证配置

```bash
# === 使用 htpasswd 基本认证 ===

# 创建认证文件
mkdir -p /opt/registry/auth

# 安装 htpasswd 工具
apt-get install apache2-utils

# 创建用户 (首次使用 -B 强制 bcrypt)
htpasswd -Bbc /opt/registry/auth/htpasswd admin admin_password
htpasswd -Bb /opt/registry/auth/htpasswd developer dev_password

# 使用 Docker 运行 htpasswd
docker run --rm --entrypoint htpasswd httpd:2 -Bbc /opt/registry/auth/htpasswd admin admin_password

# === 带认证的 Registry 配置 ===
cat > /opt/registry/config/config.yml << 'EOF'
version: 0.1
log:
  level: info
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
http:
  addr: :443
  tls:
    certificate: /certs/registry.crt
    key: /certs/registry.key
  headers:
    X-Content-Type-Options: [nosniff]
auth:
  htpasswd:
    realm: "Registry Realm"
    path: /auth/htpasswd
EOF

# 启动带认证的 Registry
docker run -d --name registry \
    -p 443:443 \
    -v /opt/registry/data:/var/lib/registry \
    -v /opt/registry/certs:/certs:ro \
    -v /opt/registry/auth:/auth:ro \
    -v /opt/registry/config/config.yml:/etc/docker/registry/config.yml:ro \
    --restart unless-stopped \
    registry:2

# 登录
docker login registry.example.com
# Username: admin
# Password: ****

# 登录信息保存在 ~/.docker/config.json
cat ~/.docker/config.json
```

#### 2.6 Registry 存储后端配置

```yaml
# S3 存储后端
version: 0.1
storage:
  s3:
    accesskey: AKIAIOSFODNN7EXAMPLE
    secretkey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region: us-east-1
    regionendpoint: https://s3.amazonaws.com
    bucket: my-registry-bucket
    encrypt: true
    secure: true
    rootdirectory: /registry
    chunksize: 5242880  # 5MB
  cache:
    blobdescriptor: inmemory
  delete:
    enabled: true

# MinIO (S3 兼容)
storage:
  s3:
    accesskey: minioadmin
    secretkey: minioadmin
    region: us-east-1
    regionendpoint: http://minio:9000
    bucket: registry
    secure: false
    skipverify: false

# Azure Blob Storage
storage:
  azure:
    accountname: myaccount
    accountkey: mybase64encodedkey
    container: registry
    realm: core.windows.net

# Google Cloud Storage
storage:
  gcs:
    bucket: my-registry-bucket
    keyfile: /path/to/keyfile.json
    rootdirectory: /registry
    chunksize: 5242880
```

---

### 3. Harbor 企业级私有仓库

#### 3.1 Harbor 架构

```
Harbor 架构:

┌──────────────────────────────────────────────────────────┐
│                    Harbor 整体架构                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Nginx (反向代理 + TLS)               │   │
│  │           :443 (HTTPS) / :80 (HTTP)              │   │
│  └────────────┬─────────────────┬───────────────────┘   │
│               │                 │                        │
│  ┌────────────┴──┐   ┌─────────┴─────────┐             │
│  │  Harbor Core  │   │  Harbor Portal    │             │
│  │  (API + 业务) │   │  (Web UI)         │             │
│  │               │   │  React 前端        │             │
│  │  - 项目管理    │   │                   │             │
│  │  - 用户管理    │   └───────────────────┘             │
│  │  - 镜像管理    │                                      │
│  │  - 配额管理    │                                      │
│  └───────┬───────┘                                      │
│          │                                               │
│  ┌───────┴───────────────────────────────────────────┐  │
│  │                 核心组件                            │  │
│  │                                                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐ │  │
│  │  │ Registry   │ │ Job Service│ │ Trivy Scanner  │ │  │
│  │  │ (v2)       │ │ (异步任务)  │ │ (漏洞扫描)      │ │  │
│  │  └────────────┘ └────────────┘ └────────────────┘ │  │
│  │                                                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐ │  │
│  │  │ Registry   │ │ Notary     │ │ Chart Museum   │ │  │
│  │  │ Controller │ │ (镜像签名)  │ │ (Helm Chart)   │ │  │
│  │  └────────────┘ └────────────┘ └────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │                 数据存储                            │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐ │  │
│  │  │ PostgreSQL │ │    Redis   │ │  镜像存储       │ │  │
│  │  │ (元数据)    │ │ (缓存+队列)│ │ (本地/S3/...)  │ │  │
│  │  └────────────┘ └────────────┘ └────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

#### 3.2 Harbor 安装

```bash
# === 安装前准备 ===

# 1. 系统要求
# - CPU: 2 核以上
# - 内存: 4GB 以上
# - 磁盘: 40GB 以上
# - Docker: 20.10+
# - Docker Compose: v2+

# 2. 安装 Docker Compose (如果未安装)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# === 下载 Harbor ===
HARBOR_VERSION=v2.10.0
wget https://github.com/goharbor/harbor/releases/download/${HARBOR_VERSION}/harbor-offline-installer-${HARBOR_VERSION}.tgz

# 解压
tar xzf harbor-offline-installer-${HARBOR_VERSION}.tgz
cd harbor

# === 配置 Harbor ===
cp harbor.yml.tmpl harbor.yml

# 编辑配置文件
cat > harbor.yml << 'EOF'
# 访问地址
hostname: registry.example.com

# HTTP 配置
http:
  port: 80

# HTTPS 配置 (生产必须)
https:
  port: 443
  certificate: /opt/harbor/certs/registry.crt
  private_key: /opt/harbor/certs/registry.key

# 管理员初始密码 (必须修改)
harbor_admin_password: Harbor12345

# 数据库配置
database:
  password: root123
  max_idle_conns: 100
  max_open_conns: 900
  conn_max_lifetime: 5m
  conn_max_idle_time: 0

# 数据存储路径
data_volume: /data/harbor

# 镜像存储后端 (默认本地文件系统)
storage_service:
  filesystem:
    maxthreads: 100
  # S3 存储 (可选)
  # s3:
  #   accesskey: AKIAIOSFODNN7EXAMPLE
  #   secretkey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  #   region: us-east-1
  #   bucket: harbor-registry

# Trivy 漏洞扫描
trivy:
  ignore_unfixed: false
  security_check: vuln
  insecure: false

# 日志配置
log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor

# 镜像复制并发数
max_job_workers: 10

# 项目配额
project_quota:
  default_storage_per_project: -1  # -1 表示不限制 (字节)
EOF

# === 安装 Harbor ===
# 带 Trivy 扫描器
sudo ./install.sh --with-trivy

# 带 Notary 签名支持
# sudo ./install.sh --with-trivy --with-notary

# 带 Chart Museum (Helm Chart 仓库)
# sudo ./install.sh --with-trivy --with-chartmuseum

# === 验证安装 ===
docker compose ps
# 应该看到所有 Harbor 组件都在运行:
# harbor-core, harbor-db, harbor-jobservice, harbor-log,
# harbor-portal, nginx, redis, registry, registryctl, trivy-adapter

# 访问 Web UI
# https://registry.example.com
# 用户名: admin
# 密码: Harbor12345 (首次登录后修改)
```

#### 3.3 Harbor 核心功能

```bash
# === 项目管理 ===
# Harbor 使用项目 (Project) 组织镜像
# 每个项目可以设置:
# - 访问级别: 公开/私有
# - 存储配额
# - 漏洞扫描策略
# - 镜像保留策略
# - 镜像复制策略

# === 通过 API 操作 Harbor ===

# 登录获取 token
TOKEN=$(curl -s -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/users" \
    -H "X-Is-Resource-Name: false" | jq -r '.[0].user_id')

# 创建项目
curl -k -u admin:Harbor12345 \
    -X POST "https://registry.example.com/api/v2.0/projects" \
    -H "Content-Type: application/json" \
    -d '{
        "project_name": "myproject",
        "public": false,
        "storage_limit": -1,
        "metadata": {
            "auto_scan": "true",
            "severity": "high"
        }
    }'

# 列出项目
curl -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/projects" | jq

# 列出项目中的镜像仓库
curl -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/projects/myproject/repositories" | jq

# 获取镜像标签
curl -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/projects/myproject/repositories/myapp/artifacts" | jq
```

#### 3.4 Harbor Web UI 功能

```
Harbor Web UI 功能概览:

┌──────────────────────────────────────────────────────┐
│  Harbor Web UI                                       │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 项目管理  │  │  镜像库   │  │  系统管理        │  │
│  │          │  │          │  │                  │  │
│  │ - 创建   │  │ - 列表   │  │ - 用户管理       │  │
│  │ - 配额   │  │ - 标签   │  │ - 项目成员       │  │
│  │ - 成员   │  │ - 漏洞   │  │ - 认证方式       │  │
│  │ - 策略   │  │ - 签名   │  │ - 镜像复制       │  │
│  └──────────┘  │ - SBOM   │  │ - 垃圾回收       │  │
│                └──────────┘  │ - 系统配置       │  │
│                              │ - 审计日志       │  │
│  ┌──────────────────────────┐│ - 配额管理       │  │
│  │  安全扫描                │└──────────────────┘  │
│  │                          │                      │
│  │ - 自动扫描               │ ┌──────────────────┐  │
│  │ - 手动扫描               │ │  镜像保留        │  │
│  │ - 漏洞报告               │ │                  │  │
│  │ - 扫描器配置              │ │ - Tag 规则       │  │
│  └──────────────────────────┘│ - 保留策略       │  │
│                              │ - 标签不可变      │  │
│                              └──────────────────┘  │
└──────────────────────────────────────────────────────┘
```

#### 3.5 Harbor 镜像推送与拉取

```bash
# === 配置客户端 ===

# 1. 信任 Harbor 的 TLS 证书
sudo mkdir -p /etc/docker/certs.d/registry.example.com
sudo cp /opt/harbor/certs/ca.crt /etc/docker/certs.d/registry.example.com/ca.crt
sudo systemctl restart docker

# 2. 登录 Harbor
docker login registry.example.com
# Username: admin
# Password: ****

# === 推送镜像 ===

# 1. 给镜像打标签 (格式: harbor地址/项目名/镜像名:标签)
docker tag myapp:latest registry.example.com/myproject/myapp:v1
docker tag myapp:latest registry.example.com/myproject/myapp:latest

# 2. 推送
docker push registry.example.com/myproject/myapp:v1
docker push registry.example.com/myproject/myapp:latest

# === 拉取镜像 ===
docker pull registry.example.com/myproject/myapp:v1

# === 在 Kubernetes 中使用 Harbor ===
# 创建 imagePullSecret
kubectl create secret docker-registry harbor-creds \
    --docker-server=registry.example.com \
    --docker-username=admin \
    --docker-password=Harbor12345 \
    --docker-email=admin@example.com

# 在 Pod 中使用
# image: registry.example.com/myproject/myapp:v1
# imagePullSecrets:
#   - name: harbor-creds
```

#### 3.6 Harbor 漏洞扫描

```bash
# === 自动扫描 ===
# 在项目设置中启用 "自动扫描"
# 推送镜像时自动触发 Trivy 扫描

# === 手动扫描 ===
# 通过 Web UI: 进入镜像详情页，点击 "Scan"
# 通过 API:
curl -k -u admin:Harbor12345 \
    -X POST "https://registry.example.com/api/v2.0/projects/myproject/repositories/myapp/artifacts/v1/scan"

# 查看扫描结果
curl -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/projects/myproject/repositories/myapp/artifacts/v1?with_scan_overview=true" | jq '.scan_overview'

# === 扫描策略 ===
# 1. 阻止拉取有高危漏洞的镜像
#    项目设置 → 漏洞阻止策略 → 选择严重级别

# 2. 定期重新扫描
#    系统管理 → 扫描器 → 一键扫描所有

# 3. 自定义 CVE 白名单
#    系统管理 → 系统配置 → 漏洞白名单
```

---

### 4. 镜像垃圾回收

#### 4.1 Registry v2 垃圾回收

```bash
# === Registry v2 垃圾回收流程 ===

# 1. 启用删除功能 (config.yml)
# storage:
#   delete:
#     enabled: true

# 2. 删除镜像 tag (通过 API 或 Harbor UI)
# 删除只是标记删除，不会释放空间

# 3. 运行垃圾回收
docker exec registry bin/registry garbage-collect \
    /etc/docker/registry/config.yml

# 带详细输出
docker exec registry bin/registry garbage-collect \
    --delete-untagged \
    /etc/docker/registry/config.yml

# === 定时垃圾回收脚本 ===
cat > /opt/registry/gc.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

REGISTRY_CONTAINER="registry"
LOG_FILE="/var/log/registry-gc.log"

echo "$(date): Starting garbage collection..." >> "$LOG_FILE"

# 停止 Registry (避免写入冲突)
docker stop "$REGISTRY_CONTAINER"

# 运行垃圾回收
docker run --rm \
    -v /opt/registry/data:/var/lib/registry \
    -v /opt/registry/config/config.yml:/etc/docker/registry/config.yml:ro \
    registry:2 \
    bin/registry garbage-collect --delete-untagged /etc/docker/registry/config.yml \
    >> "$LOG_FILE" 2>&1

# 重启 Registry
docker start "$REGISTRY_CONTAINER"

echo "$(date): Garbage collection completed." >> "$LOG_FILE"
SCRIPT

chmod +x /opt/registry/gc.sh

# 添加到 crontab (每天凌晨 3 点执行)
echo "0 3 * * * /opt/registry/gc.sh" | crontab -
```

#### 4.2 Harbor 垃圾回收

```bash
# === 通过 Web UI ===
# 系统管理 → 垃圾回收 → 立即执行

# === 通过 API ===
# 创建垃圾回收任务
curl -k -u admin:Harbor12345 \
    -X POST "https://registry.example.com/api/v2.0/system/gc/schedule" \
    -H "Content-Type: application/json" \
    -d '{
        "parameters": {
            "delete_untagged": true,
            "dry_run": false
        },
        "schedule": {
            "type": "Weekly",
            "cron": "0 0 0 * * 0"
        }
    }'

# 查看 GC 任务状态
curl -k -u admin:Harbor12345 \
    "https://registry.example.com/api/v2.0/system/gc" | jq

# === Harbor GC 工作原理 ===
# 1. 标记阶段: 扫描所有引用，标记仍被使用的 blob
# 2. 清除阶段: 删除未被标记的 blob
# 3. Harbor 特性:
#    - 在线 GC (不需要停机)
#    - 支持 dry-run 模式
#    - 支持定时执行
#    - GC 日志和历史记录
```

#### 4.3 镜像保留策略

```yaml
# Harbor 镜像保留策略 (Tag Retention)
# 配合 GC 实现自动化镜像生命周期管理

# 示例策略:
# 1. 保留最近 10 个标签
# 2. 保留最近 30 天的标签
# 3. 保留所有以 "release-" 开头的标签
# 4. 保留所有语义化版本标签 (v1.0.0)

# 通过 API 创建保留策略:
# POST /api/v2.0/projects/{project_name}/retentions
{
    "algorithm": "or",
    "rules": [
        {
            "disabled": false,
            "action": "retain",
            "template": "latestPushedK",
            "params": {
                "latestPushedK": 10
            },
            "tag_selectors": [
                {
                    "kind": "doublestar",
                    "decoration": "matches",
                    "pattern": "**"
                }
            ],
            "repo_selectors": [
                {
                    "kind": "doublestar",
                    "decoration": "repoMatches",
                    "pattern": "**"
                }
            ]
        },
        {
            "disabled": false,
            "action": "retain",
            "template": "latestPulledN",
            "params": {
                "latestPulledN": 5
            },
            "tag_selectors": [
                {
                    "kind": "doublestar",
                    "decoration": "matches",
                    "pattern": "**"
                }
            ],
            "repo_selectors": [
                {
                    "kind": "doublestar",
                    "decoration": "repoMatches",
                    "pattern": "**"
                }
            ]
        }
    ],
    "scope": {
        "level": "project",
        "ref": 1
    },
    "trigger": {
        "kind": "scheduled",
        "settings": {
            "cron": "0 0 2 * * *"
        }
    }
}
```

---

### 5. Harbor 高可用

#### 5.1 Harbor 高可用架构

```
Harbor 高可用部署架构:

┌─────────────────────────────────────────────────────────┐
│                  负载均衡器 (HAProxy/Nginx)               │
│                  VIP: 10.0.1.100:443                     │
└────────────────┬────────────────────┬───────────────────┘
                 │                    │
    ┌────────────┴──────┐   ┌────────┴────────┐
    │   Harbor Node 1   │   │  Harbor Node 2   │
    │   10.0.1.101      │   │  10.0.1.102      │
    │                   │   │                  │
    │  ┌─────────────┐  │   │ ┌─────────────┐  │
    │  │   Nginx     │  │   │ │   Nginx     │  │
    │  │   Core      │  │   │ │   Core      │  │
    │  │   Portal    │  │   │ │   Portal    │  │
    │  │   Job Svc   │  │   │ │   Job Svc   │  │
    │  │   Trivy     │  │   │ │   Trivy     │  │
    │  └──────┬──────┘  │   │ └──────┬──────┘  │
    │         │         │   │        │         │
    └─────────┼─────────┘   └────────┼─────────┘
              │                      │
    ┌─────────┴──────────────────────┴─────────┐
    │              共享存储层                     │
    │                                           │
    │  ┌─────────────┐  ┌──────────────────┐   │
    │  │  PostgreSQL  │  │   Redis Cluster  │   │
    │  │  (主从复制)   │  │   (Sentinel)     │   │
    │  │  10.0.1.103  │  │   10.0.1.103    │   │
    │  │  10.0.1.104  │  │   10.0.1.104    │   │
    │  └─────────────┘  └──────────────────┘   │
    │                                           │
    │  ┌──────────────────────────────────┐     │
    │  │       共享镜像存储                │     │
    │  │  NFS / S3 / MinIO / Ceph         │     │
    │  │  (所有节点读写同一存储)            │     │
    │  └──────────────────────────────────┘     │
    └───────────────────────────────────────────┘
```

#### 5.2 Harbor 高可用配置

```yaml
# harbor.yml (Node 1)
hostname: harbor.example.com
# ... 其他配置同单节点

# 共享数据库
database:
  type: external
  external:
    host: 10.0.1.103
    port: 5432
    username: harbor
    password: db_password
    ssl_mode: require

# 共享 Redis
redis:
  type: external
  external:
    addr: 10.0.1.103:6379
    password: redis_password
    sentinel_master_set: harbor
    sentinel_addrs: 10.0.1.103:26379,10.0.1.104:26379

# 共享存储
storage_service:
  s3:
    accesskey: AKIAIOSFODNN7EXAMPLE
    secretkey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    region: us-east-1
    regionendpoint: https://minio.example.com
    bucket: harbor-registry
    secure: true
```

```bash
# === 负载均衡器配置 (HAProxy) ===
cat > /etc/haproxy/haproxy.cfg << 'EOF'
global
    maxconn 4096
    log /dev/log local0

defaults
    log global
    mode tcp
    option tcplog
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend harbor_https
    bind *:443
    default_backend harbor_backend

backend harbor_backend
    balance roundrobin
    option httpchk GET /api/v2.0/health
    http-check expect status 200
    server harbor1 10.0.1.101:443 check check-ssl verify none
    server harbor2 10.0.1.102:443 check check-ssl verify none

frontend harbor_http
    bind *:80
    default_backend harbor_http_backend

backend harbor_http_backend
    balance roundrobin
    option httpchk GET /api/v2.0/health
    server harbor1 10.0.1.101:80 check
    server harbor2 10.0.1.102:80 check
EOF

systemctl restart haproxy
```

#### 5.3 Harbor 跨数据中心镜像复制

```
跨数据中心镜像复制:

┌──────────────────┐         ┌──────────────────┐
│  Harbor (北京)    │         │  Harbor (上海)    │
│  bj.registry.com │ ◄─────▶ │  sh.registry.com │
│                  │         │                  │
│  ┌────────────┐  │  Push/  │  ┌────────────┐  │
│  │ Project A  │  │  Pull   │  │ Project A  │  │
│  │ ┌────────┐ │  │         │  │ ┌────────┐ │  │
│  │ │ myapp  │ │──┼─────────┼──│ │ myapp  │ │  │
│  │ │ v1     │ │  │         │  │ │ v1     │ │  │
│  │ └────────┘ │  │         │  │ └────────┘ │  │
│  └────────────┘  │         │  └────────────┘  │
│                  │         │                  │
│  Replication     │         │  Replication     │
│  Policy:         │         │  Policy:         │
│  - Push to SH    │         │  - Push to BJ    │
│  - Event-based   │         │  - Event-based   │
└──────────────────┘         └──────────────────┘
```

```bash
# === 配置镜像复制 ===

# 1. 添加目标 Harbor 实例 (注册表)
curl -k -u admin:Harbor12345 \
    -X POST "https://bj.registry.example.com/api/v2.0/registries" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "sh-harbor",
        "type": "harbor",
        "url": "https://sh.registry.example.com",
        "credential": {
            "type": "basic",
            "access_key": "admin",
            "access_secret": "Harbor12345"
        },
        "insecure": false
    }'

# 2. 创建复制策略
curl -k -u admin:Harbor12345 \
    -X POST "https://bj.registry.example.com/api/v2.0/replication/policies" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "sync-to-shanghai",
        "src_registry": null,
        "dest_registry": {
            "id": 1
        },
        "dest_namespace": "",
        "trigger": {
            "type": "event_based",
            "trigger_settings": {}
        },
        "filters": [
            {
                "type": "name",
                "value": "myproject/**"
            },
            {
                "type": "tag",
                "value": "v*"
            }
        ],
        "enabled": true,
        "override": true,
        "speed": -1
    }'

# 3. 手动触发复制
curl -k -u admin:Harbor12345 \
    -X POST "https://bj.registry.example.com/api/v2.0/replication/executions" \
    -H "Content-Type: application/json" \
    -d '{"policy_id": 1}'
```

---

### 6. 生产环境最佳实践

#### 6.1 安全配置

```bash
# === 1. 修改默认密码 ===
# 首次登录后立即修改 admin 密码

# === 2. 启用 HTTPS ===
# 生产环境必须使用 TLS

# === 3. 配置认证方式 ===
# 集成 LDAP/AD/OIDC
# harbor.yml 中配置:
# auth_mode: ldap_auth
# ldap:
#   url: ldap://ldap.example.com
#   base_dn: dc=example,dc=com
#   search_dn: cn=admin,dc=example,dc=com
#   search_password: ldap_password
#   uid: uid
#   group_base_dn: ou=groups,dc=example,dc=com

# === 4. 启用审计日志 ===
# 所有操作自动记录审计日志
# 可通过 API 或 UI 查看

# === 5. 配置项目配额 ===
# 防止单个项目占用过多存储
# 每个项目设置存储限制

# === 6. 启用漏洞扫描阻断 ===
# 配置项目策略: 阻止拉取有高危漏洞的镜像

# === 7. 镜像签名 ===
# 集成 Cosign 或 Notary

# === 8. 网络安全 ===
# 防火墙只开放 80/443 端口
# 内部组件使用内部网络
```

#### 6.2 监控与告警

```yaml
# Harbor 监控配置
# Harbor 暴露 Prometheus 指标端点

# Prometheus 配置
scrape_configs:
  - job_name: 'harbor'
    metrics_path: /metrics
    scheme: https
    tls_config:
      insecure_skip_verify: true
    basic_auth:
      username: admin
      password: Harbor12345
    static_configs:
      - targets:
          - 'harbor.example.com:443'

# 关键监控指标:
# harbor_project_total - 项目总数
# harbor_repository_total - 镜像仓库总数
# harbor_artifact_total - 镜像 artifact 总数
# harbor_project_quota_usage_byte - 项目配额使用量
# harbor_chart_total - Helm Chart 总数
# harbor_gc_duration_seconds - GC 耗时
# harbor_scanner_* - 扫描器相关指标
```

```yaml
# Grafana Dashboard 示例告警规则
groups:
  - name: harbor
    rules:
      - alert: HarborDown
        expr: up{job="harbor"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Harbor instance is down"

      - alert: HarborDiskUsageHigh
        expr: (node_filesystem_avail_bytes{mountpoint="/data/harbor"} / node_filesystem_size_bytes{mountpoint="/data/harbor"}) < 0.15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Harbor disk usage is above 85%"

      - alert: HarborProjectQuotaNearLimit
        expr: harbor_project_quota_usage_byte / harbor_project_quota_byte > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Harbor project quota usage above 90%"
```

#### 6.3 备份与恢复

```bash
# === Harbor 备份脚本 ===
cat > /opt/harbor/backup.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backup/harbor/$(date +%Y%m%d_%H%M%S)"
HARBOR_DIR="/opt/harbor"

mkdir -p "$BACKUP_DIR"

echo "Starting Harbor backup..."

# 1. 备份配置文件
cp -r "$HARBOR_DIR/harbor.yml" "$BACKUP_DIR/"
cp -r "$HARBOR_DIR/docker-compose.yml" "$BACKUP_DIR/"

# 2. 备份数据库
docker exec harbor-db pg_dump -U postgres registry > "$BACKUP_DIR/registry.sql"
echo "Database backup completed."

# 3. 备份镜像数据 (增量)
# rsync -av --delete /data/harbor/ "$BACKUP_DIR/harbor_data/"
tar czf "$BACKUP_DIR/harbor_data.tar.gz" -C /data/harbor .
echo "Data backup completed."

# 4. 备份密钥和证书
cp -r /data/harbor/secret "$BACKUP_DIR/"

# 5. 清理旧备份 (保留 30 天)
find /backup/harbor -maxdepth 1 -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
SCRIPT

chmod +x /opt/harbor/backup.sh

# === Harbor 恢复步骤 ===
# 1. 安装相同版本的 Harbor
# 2. 停止 Harbor: docker compose down
# 3. 恢复数据库: psql -U postgres registry < registry.sql
# 4. 恢复镜像数据: tar xzf harbor_data.tar.gz -C /data/harbor/
# 5. 恢复密钥: cp -r secret /data/harbor/
# 6. 启动 Harbor: docker compose up -d
```

---

## 💻 实战练习

### 练习 1: 部署基础 Registry

**目标:** 部署带 TLS 和认证的 Docker Registry v2。

```bash
# 任务:
# 1. 生成自签名证书
# 2. 创建 htpasswd 认证文件
# 3. 编写 Registry 配置文件
# 4. 使用 docker compose 部署
# 5. 登录、推送、拉取镜像
# 6. 通过 API 查看 catalog

# 参考 docker-compose.yml:
services:
  registry:
    image: registry:2
    ports:
      - "443:443"
    volumes:
      - registry_data:/var/lib/registry
      - ./certs:/certs:ro
      - ./auth:/auth:ro
      - ./config.yml:/etc/docker/registry/config.yml:ro
    environment:
      REGISTRY_HTTP_ADDR: "0.0.0.0:443"
      REGISTRY_HTTP_TLS_CERTIFICATE: /certs/registry.crt
      REGISTRY_HTTP_TLS_KEY: /certs/registry.key
    restart: unless-stopped

volumes:
  registry_data:
```

### 练习 2: 安装 Harbor

**目标:** 完成 Harbor 的完整安装流程。

```bash
# 任务:
# 1. 下载 Harbor 离线安装包
# 2. 配置 harbor.yml
# 3. 运行 install.sh
# 4. 通过 Web UI 创建项目
# 5. 推送镜像到 Harbor
# 6. 配置自动扫描
# 7. 运行垃圾回收

# 验证清单:
# [ ] Web UI 可访问
# [ ] 能创建项目
# [ ] 能推送镜像
# [ ] 能拉取镜像
# [ ] 漏洞扫描正常工作
# [ ] 垃圾回收正常工作
```

### 练习 3: CI/CD 集成

**目标:** 将 Harbor 集成到 CI/CD 流水线中。

```yaml
# GitHub Actions 示例
name: Build and Push to Harbor
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Harbor
        run: |
          echo "${{ secrets.HARBOR_PASSWORD }}" | \
          docker login registry.example.com -u ${{ secrets.HARBOR_USERNAME }} --password-stdin

      - name: Build and push
        run: |
          docker build -t registry.example.com/myproject/myapp:${{ github.ref_name }} .
          docker push registry.example.com/myproject/myapp:${{ github.ref_name }}

      - name: Wait for scan
        run: sleep 60

      - name: Check scan results
        run: |
          # 使用 Harbor API 检查扫描结果
          curl -k -u ${{ secrets.HARBOR_USERNAME }}:${{ secrets.HARBOR_PASSWORD }} \
            "https://registry.example.com/api/v2.0/projects/myproject/repositories/myapp/artifacts/${{ github.ref_name }}?with_scan_overview=true" | \
            jq '.scan_overview["application/vnd.security.vulnerability.report; version=1.1"].severity'
```

---

## 🎯 面试题精选

### 1. Docker Registry v2 和 Harbor 有什么区别？

**参考答案:**

Docker Registry v2 是基础的镜像存储服务，只提供镜像推送/拉取 API，没有 UI、认证、扫描等企业功能。

Harbor 基于 Registry v2 构建，增加了:
- Web UI 管理界面
- 基于项目的 RBAC 权限管理
- 集成 Trivy 漏洞扫描
- 镜像复制（跨数据中心同步）
- 镜像签名验证
- 垃圾回收管理
- 配额管理
- 审计日志
- LDAP/AD/OIDC 认证集成

Harbor 是 CNCF 毕业项目，是企业级私有仓库的标准选择。

### 2. 如何配置 Docker 客户端信任自签名证书？

**参考答案:**

两种方式:
1. **推荐**: 将 CA 证书安装到 `/etc/docker/certs.d/<registry-domain>/ca.crt`，重启 Docker 服务
2. **不推荐**: 在 `/etc/docker/daemon.json` 中添加 `insecure-registries`，这种方式不验证证书，存在安全风险

对于生产环境，建议使用 Let's Encrypt 或企业 CA 签发的正式证书。

### 3. Harbor 的垃圾回收机制是怎样的？

**参考答案:**

Harbor 的垃圾回收分两步:
1. **标记阶段**: 扫描所有镜像引用，标记仍在使用的 blob（层数据）
2. **清除阶段**: 删除未被标记的 blob

关键点:
- Harbor 支持在线 GC（不需要停机）
- 支持 dry-run 模式预览将删除的内容
- 支持定时执行（cron 表达式）
- GC 前应先删除不需要的 tag（通过保留策略或手动删除）
- `delete_untagged` 选项可清理无 tag 的悬空镜像

### 4. 如何实现 Harbor 的高可用？

**参考答案:**

核心策略:
1. **外部数据库**: 使用 PostgreSQL 主从复制，所有 Harbor 节点连接同一个外部数据库
2. **外部 Redis**: 使用 Redis Sentinel 或 Cluster，保证缓存和队列的高可用
3. **共享存储**: 使用 NFS、S3、MinIO 等共享存储后端，所有节点读写同一存储
4. **负载均衡**: 使用 HAProxy 或云负载均衡器分发请求到多个 Harbor 节点
5. **镜像复制**: 跨数据中心使用 Harbor 内置的镜像复制功能同步

### 5. 如何在 CI/CD 流水线中安全地使用私有仓库？

**参考答案:**

1. 使用 CI/CD 系统的密钥管理功能存储仓库凭证
2. 在流水线中使用 `docker login --password-stdin` 避免密码出现在命令行
3. 推送后等待漏洞扫描完成，根据扫描结果决定是否继续部署
4. 使用镜像签名（Cosign）验证镜像来源
5. 部署前验证镜像签名
6. 使用 ServiceAccount 或 Robot Account 限制权限

### 6. 镜像推送的完整流程是什么？

**参考答案:**

```
docker push myregistry.com/myapp:v1

1. docker client → 认证 (Bearer Token / Basic Auth)
2. 检查镜像 manifest 是否已存在 (HEAD /v2/name/manifests/ref)
3. 对于每个 layer blob:
   a. 检查 blob 是否存在 (HEAD /v2/name/blobs/digest)
   b. 不存在则发起上传 (POST /v2/name/blobs/uploads)
   c. 上传 blob 数据 (PATCH /v2/name/blobs/uploads/uuid)
   d. 完成上传 (PUT /v2/name/blobs/uploads/uuid?digest=...)
4. 上传 manifest (PUT /v2/name/manifests/ref)
5. 服务端验证 manifest 完整性
```

### 7. Harbor 的项目配额如何工作？

**参考答案:**

Harbor 项目配额限制单个项目的存储使用量:
- 管理员可以设置全局默认配额
- 可以为单个项目设置独立配额
- 配额计算包括所有 tag 和 artifact 的 blob 大小
- 推送镜像前检查，超出配额则拒绝推送
- 删除镜像后需要运行 GC 才能释放配额空间

### 8. 如何从 Harbor 迁移到其他私有仓库？

**参考答案:**

1. **镜像复制**: 使用 Harbor 的复制功能将镜像推送到新仓库
2. **脚本批量拉取推送**: 编写脚本从旧仓库拉取、打标签、推送到新仓库
3. **Skopeo 工具**: 使用 `skopeo copy` 直接在仓库间复制镜像
4. **数据迁移**: 直接复制存储数据（仅限同类型存储后端）

迁移步骤:
1. 在新仓库创建对应项目
2. 配置镜像复制或编写迁移脚本
3. 验证镜像完整性
4. 更新 CI/CD 和 K8s 中的镜像地址
5. 下线旧仓库

### 9. 什么是 Robot Account？有什么用途？

**参考答案:**

Robot Account 是 Harbor 中用于自动化系统的专用账户:
- 不是真实的用户，而是为 CI/CD、自动化脚本等创建的服务账户
- 可以细粒度分配权限（只允许 push/pull 特定项目）
- 支持设置过期时间
- 密码可随时重新生成
- 不占用用户许可证

使用场景: CI/CD 流水线推送镜像、自动化扫描、跨 Harbor 复制。

### 10. 如何监控私有仓库的健康状态？

**参考答案:**

1. **API 健康检查**: 定期调用 `/api/v2.0/health` 端点
2. **Prometheus 指标**: Harbor 暴露 `/metrics` 端点，监控项目数、镜像数、存储使用等
3. **日志监控**: 收集 Harbor 各组件日志，使用 ELK/Loki 分析
4. **存储监控**: 监控磁盘使用率，设置告警阈值
5. **扫描监控**: 监控扫描队列长度和扫描失败率
6. **复制监控**: 监控跨数据中心复制的状态和延迟

---

## 📚 深入阅读

- [Docker Registry v2 官方文档](https://docs.docker.com/registry/)
- [Docker Registry v2 API](https://docs.docker.com/registry/spec/api/)
- [Harbor 官方文档](https://goharbor.io/docs/)
- [Harbor GitHub](https://github.com/goharbor/harbor)
- [Harbor 安装指南](https://goharbor.io/docs/latest/install-config/)
- [Harbor 高可用部署](https://goharbor.io/docs/latest/install-config/harbor-ha-helm/)
- [Harbor API 参考](https://goharbor.io/docs/latest/administration/vulnerability-scanning/)
- [Skopeo - 镜像工具](https://github.com/containers/skopeo)
- [Cosign - 镜像签名](https://docs.sigstore.dev/cosign/overview/)
- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec)

---

## ✅ 自检清单

- [ ] 理解企业为什么需要私有镜像仓库
- [ ] 能部署带 TLS 和认证的 Docker Registry v2
- [ ] 掌握镜像推送/拉取的完整流程
- [ ] 理解 Registry v2 的存储结构
- [ ] 能配置自签名证书并让客户端信任
- [ ] 能安装和配置 Harbor
- [ ] 掌握 Harbor 的项目管理和权限配置
- [ ] 能配置漏洞自动扫描和阻断策略
- [ ] 理解垃圾回收的原理和配置方法
- [ ] 能配置镜像保留策略
- [ ] 理解 Harbor 高可用架构（外部 DB、共享存储）
- [ ] 能配置跨数据中心镜像复制
- [ ] 掌握 Harbor 的备份与恢复
- [ ] 能将私有仓库集成到 CI/CD 流水线
