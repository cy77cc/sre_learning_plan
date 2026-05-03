# Day 156: 密钥管理 — Vault

> 📅 日期：2026-05-03
> 📖 学习主题：Vault 架构、Secret Engine、Auth Method、策略、动态密钥、自动轮换、K8s 集成、外部密钥管理
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 93-104（K8s 基础）、Day 152-155（CI/CD 流程与部署策略）

## 🎯 学习目标

- 理解 HashiCorp Vault 的架构和核心概念
- 掌握 Secret Engine 的类型和使用场景
- 精通 Auth Method 的配置和管理
- 理解 Vault 策略（Policy）和权限控制
- 能够配置动态密钥生成和自动轮换
- 掌握 Vault 与 Kubernetes 的集成方式
- 了解 External Secrets Operator 和 CSI Secret Store
- 能够设计企业级密钥管理方案

---

## 📖 核心知识点

### 1. Vault 架构

#### 1.1 为什么需要 Vault

```
┌─────────────────────────────────────────────────────────────────────┐
│                    为什么需要密钥管理                                 │
│                                                                     │
│  传统密钥管理的问题：                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. 密钥硬编码                                                │   │
│  │     - 数据库密码写在代码中                                    │   │
│  │     - API Key 存储在配置文件                                  │   │
│  │     - 容易泄露到 Git 仓库                                     │   │
│  │                                                             │   │
│  │  2. 密钥分散管理                                              │   │
│  │     - 每个服务自己管理密钥                                    │   │
│  │     - 没有统一的密钥管理平台                                  │   │
│  │     - 密钥版本混乱                                            │   │
│  │                                                             │   │
│  │  3. 密钥轮换困难                                              │   │
│  │     - 手动轮换，容易遗漏                                      │   │
│  │     - 轮换需要重启服务                                        │   │
│  │     - 没有自动化机制                                          │   │
│  │                                                             │   │
│  │  4. 审计困难                                                  │   │
│  │     - 谁在什么时候访问了什么密钥？                            │   │
│  │     - 没有访问日志                                            │   │
│  │     - 合规要求难以满足                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Vault 解决方案：                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ✅ 集中管理：所有密钥在一个平台管理                          │   │
│  │  ✅ 动态密钥：按需生成，自动过期                              │   │
│  │  ✅ 自动轮换：定期轮换，无需人工干预                          │   │
│  │  ✅ 审计日志：所有访问操作都有记录                            │   │
│  │  ✅ 加密即服务：提供加密/解密 API                             │   │
│  │  ✅ 细粒度权限：基于策略的访问控制                            │   │
│  │  ✅ 多后端支持：支持多种 Secret Engine                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 Vault 核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Vault 核心架构                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Client（客户端）                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ CLI      │  │ API      │  │ UI       │  │ SDK      │   │   │
│  │  │ (命令行) │  │ (HTTP)   │  │ (Web)    │  │ (程序)   │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Vault Server                              │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  API Layer（API 层）                                 │   │   │
│  │  │  - HTTP/HTTPS 接口                                   │   │   │
│  │  │  - 请求路由                                          │   │   │
│  │  │  - TLS 终止                                          │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Auth Methods（认证方法）                             │   │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │   │   │
│  │  │  │ Token  │ │ LDAP   │ │ AWS    │ │ K8s    │       │   │   │
│  │  │  │        │ │        │ │        │ │        │       │   │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘       │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Policies（策略）                                    │   │   │
│  │  │  - 定义访问权限                                      │   │   │
│  │  │  - 路径级别控制                                      │   │   │
│  │  │  - 能力（capabilities）控制                          │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Secret Engines（密钥引擎）                          │   │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │   │   │
│  │  │  │ KV     │ │Transit │ │ PKI    │ │Database│       │   │   │
│  │  │  │(静态)  │ │(加密)  │ │(证书)  │ │(动态)  │       │   │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘       │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Storage Backend（存储后端）                         │   │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │   │   │
│  │  │  │Consul  │ │ Raft   │ │ S3     │ │Postgres│       │   │   │
│  │  │  │        │ │(内置)  │ │        │ │        │       │   │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘       │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                              │                              │   │
│  │                              ▼                              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Audit Backend（审计后端）                           │   │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐                  │   │   │
│  │  │  │ File   │ │Syslog │ │Socket  │                  │   │   │
│  │  │  │        │ │        │ │        │                  │   │   │
│  │  │  └────────┘ └────────┘ └────────┘                  │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.3 Vault 核心概念

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Vault 核心概念                                     │
│                                                                     │
│  1. Seal/Unseal（封印/解封）                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Vault 启动后处于 Sealed（封印）状态                         │   │
│  │  需要提供 Unseal Key 才能解封                                │   │
│  │  Unseal Key 使用 Shamir's Secret Sharing 分片存储            │   │
│  │  生产环境使用 Auto-Unseal（KMS/HSM）自动解封                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  2. Token（令牌）                                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  所有客户端必须先认证获取 Token                              │   │
│  │  Token 是最终的授权单位                                      │   │
│  │  Token 有关联的策略（Policies）和 TTL                        │   │
│  │  Root Token 拥有最高权限（生产环境应 revoke）                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  3. Secret Engine（密钥引擎）                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Vault 的核心组件，负责生成/存储/管理密钥                    │   │
│  │  每个引擎挂载在特定路径下                                    │   │
│  │  不同引擎有不同的功能和用途                                  │   │
│  │  可以同时启用多个同类型引擎                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  4. Auth Method（认证方法）                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  定义客户端如何向 Vault 证明自己的身份                        │   │
│  │  支持多种认证方式（Token/LDAP/AWS/K8s/OIDC 等）             │   │
│  │  认证成功后获取 Token                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  5. Policy（策略）                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  定义 Token 可以访问哪些路径和执行哪些操作                   │   │
│  │  使用 HCL 格式定义                                           │   │
│  │  支持路径级别的细粒度控制                                    │   │
│  │  capabilities: create, read, update, delete, list, sudo      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.4 安装 Vault

```bash
# ===== 使用 Helm 安装 Vault（生产环境推荐）=====
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# 开发模式（学习测试）
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set "server.dev.enabled=true"

# 生产模式（HA + Raft 存储）
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set "server.ha.enabled=true" \
  --set "server.ha.raft.enabled=true" \
  --set "server.ha.replicas=3" \
  --set "server.audit.enabled=true" \
  --set "ui.enabled=true"

# ===== 使用 kubectl 安装 =====
kubectl create namespace vault

# 开发模式
kubectl run vault --image=hashicorp/vault:latest \
  --namespace vault \
  -- -dev -dev-root-token-id=root

# ===== Vault CLI 安装 =====
curl -fsSL https://releases.hashicorp.com/vault/1.15.4/vault_1.15.4_linux_amd64.zip -o vault.zip
unzip vault.zip
sudo mv vault /usr/local/bin/

# 设置环境变量
export VAULT_ADDR='http://vault.example.com:8200'
export VAULT_TOKEN='root'  # 开发模式 token
```

---

### 2. Secret Engine

#### 2.1 Secret Engine 类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Secret Engine 类型                                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  KV（Key-Value）密钥引擎                                     │   │
│  │  ├── 存储静态密钥（API Key、密码、证书等）                   │   │
│  │  ├── KV v1：简单键值存储，无版本控制                         │   │
│  │  ├── KV v2：支持版本控制、软删除、元数据                     │   │
│  │  └── 适用：应用配置、API Key、数据库密码                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Database（数据库密钥引擎）                                  │   │
│  │  ├── 动态生成数据库凭据                                      │   │
│  │  ├── 支持 MySQL/PostgreSQL/MongoDB/Oracle 等                 │   │
│  │  ├── 凭据自动过期和轮换                                      │   │
│  │  └── 适用：数据库访问凭据管理                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PKI（公钥基础设施）引擎                                     │   │
│  │  ├── 生成和管理 X.509 证书                                   │   │
│  │  ├── 内置 CA（Certificate Authority）                        │   │
│  │  ├── 支持证书自动轮换                                        │   │
│  │  └── 适用：TLS 证书、mTLS、服务间认证                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Transit（传输）引擎                                         │   │
│  │  ├── 加密即服务（Encryption as a Service）                   │   │
│  │  ├── 提供加密/解密/签名/验证 API                             │   │
│  │  ├── 密钥不离开 Vault                                        │   │
│  │  └── 适用：应用层数据加密、密钥包装                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AWS/Azure/GCP 密钥引擎                                      │   │
│  │  ├── 动态生成云厂商 IAM 凭据                                 │   │
│  │  ├── 短生命周期 Token                                        │   │
│  │  ├── 支持多种权限策略                                        │   │
│  │  └── 适用：云资源访问、CI/CD 凭据                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SSH（SSH 密钥引擎）                                         │   │
│  │  ├── SSH 签名密钥                                            │   │
│  │  ├── 短生命周期 SSH 证书                                     │   │
│  │  └── 适用：SSH 访问管理                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  KMIP（密钥管理互操作协议）引擎                               │   │
│  │  ├── 兼容 KMIP 协议                                          │   │
│  │  ├── 支持加密设备集成                                        │   │
│  │  └── 适用：企业级加密设备管理                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.2 KV Secret Engine

```bash
# ===== 启用 KV v2 引擎 =====
vault secrets enable -path=secret kv-v2

# ===== 写入密钥 =====
# 单个键值
vault kv put secret/myapp/config \
  db_host="db.example.com" \
  db_port="5432" \
  db_user="myapp" \
  db_password="super-secret-password"

# JSON 格式写入
vault kv put secret/myapp/api-keys @api-keys.json

# ===== 读取密钥 =====
# 读取最新版本
vault kv get secret/myapp/config

# 读取指定字段
vault kv get -field=db_password secret/myapp/config

# JSON 格式输出
vault kv get -format=json secret/myapp/config

# ===== 版本管理（KV v2）=====
# 查看版本历史
vault kv metadata get secret/myapp/config

# 回滚到指定版本
vault kv rollback -version=1 secret/myapp/config

# 删除指定版本
vault kv delete -versions=1 secret/myapp/config

# 恢复已删除的版本
vault kv undelete -versions=1 secret/myapp/config

# 永久删除（销毁）
vault kv destroy -versions=1 secret/myapp/config

# ===== 列出密钥 =====
vault kv list secret/myapp/
```

#### 2.3 Database Secret Engine

```bash
# ===== 启用数据库引擎 =====
vault secrets enable database

# ===== 配置数据库连接 =====
# PostgreSQL
vault write database/config/mydb \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@db.example.com:5432/mydb" \
  allowed_roles="readonly,readwrite" \
  username="vault_admin" \
  password="admin_password"

# MySQL
vault write database/config/mydb \
  plugin_name=mysql-database-plugin \
  connection_url="{{username}}:{{password}}@tcp(db.example.com:3306)/" \
  allowed_roles="readonly" \
  username="vault_admin" \
  password="admin_password"

# ===== 创建角色（动态凭据）=====
# 只读角色
vault write database/roles/readonly \
  db_name=mydb \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# 读写角色
vault write database/roles/readwrite \
  db_name=mydb \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# ===== 获取动态凭据 =====
vault read database/creds/readonly
# 输出：
# Key                Value
# ---                -----
# lease_id           database/creds/readonly/abc123
# lease_duration     1h
# password           A1b2C3d4E5f6...
# username           v-token-readonly-abc123

# ===== 撤销凭据 =====
vault lease revoke database/creds/readonly/abc123
```

#### 2.4 PKI Secret Engine

```bash
# ===== 启用 PKI 引擎 =====
vault secrets enable pki

# ===== 生成 Root CA =====
# 生成 CA 证书
vault write pki/root/generate/internal \
  common_name="Example CA" \
  ttl=87600h

# 配置 CA 证书和 CRL URL
vault write pki/config/urls \
  issuing_certificates="http://vault.example.com:8200/v1/pki/ca" \
  crl_distribution_points="http://vault.example.com:8200/v1/pki/crl"

# ===== 创建角色 =====
vault write pki/roles/myapp \
  allowed_domains="example.com" \
  allow_subdomains=true \
  max_ttl=720h \
  generate_lease=true

# ===== 签发证书 =====
vault write pki/issue/myapp \
  common_name="myapp.example.com" \
  ttl=72h

# 输出包含：certificate、issuing_ca、private_key、serial_number
```

---

### 3. Auth Method

#### 3.1 Auth Method 类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Auth Method 类型                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Token（令牌认证）                                           │   │
│  │  ├── 默认认证方式                                            │   │
│  │  ├── 直接使用 Token 访问                                    │   │
│  │  ├── 支持 Token 角色和策略                                   │   │
│  │  └── 适用：程序化访问、临时访问                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Kubernetes（K8s 认证）                                      │   │
│  │  ├── 使用 K8s Service Account Token 认证                    │   │
│  │  ├── 与 K8s 集群深度集成                                    │   │
│  │  ├── 支持基于 Namespace/ServiceAccount 的角色绑定           │   │
│  │  └── 适用：K8s Pod 中的应用访问 Vault                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AWS（AWS 认证）                                             │   │
│  │  ├── IAM 认证（EC2/Lambda/ECS）                             │   │
│  │  ├── EC2 Instance Metadata 认证                              │   │
│  │  ├── STS AssumeRole 认证                                     │   │
│  │  └── 适用：AWS 工作负载访问 Vault                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  LDAP / Active Directory                                     │   │
│  │  ├── 企业目录服务认证                                        │   │
│  │  ├── 支持用户/组映射                                         │   │
│  │  └── 适用：企业员工访问 Vault                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  OIDC / OAuth2                                               │   │
│  │  ├── 标准 OIDC 协议认证                                      │   │
│  │  ├── 支持 Google/GitHub/Okta 等 Provider                    │   │
│  │  └── 适用：Web UI 登录、SSO 集成                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  AppRole                                                     │   │
│  │  ├── 应用程序认证                                            │   │
│  │  ├── 使用 RoleID + SecretID 认证                             │   │
│  │  ├── 适合自动化场景（CI/CD）                                 │   │
│  │  └── 适用：无交互式登录的应用                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  GitHub                                                      │   │
│  │  ├── GitHub Personal Access Token 认证                       │   │
│  │  └── 适用：开发者访问 Vault                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  JWT / OIDC（通用 JWT 认证）                                 │   │
│  │  ├── 验证 JWT Token                                          │   │
│  │  ├── 支持自定义 JWT Provider                                 │   │
│  │  └── 适用：CI/CD 平台（GitHub Actions、GitLab CI）           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 Kubernetes Auth Method

```bash
# ===== 启用 Kubernetes 认证 =====
vault auth enable kubernetes

# ===== 配置 Kubernetes 认证 =====
# 方式 1: 使用 Service Account Token
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc" \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# 方式 2: 使用 Service Account（推荐）
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc" \
  kubernetes_ca_cert=@ca.crt

# ===== 创建角色 =====
# 绑定到特定 Service Account
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=myapp \
  bound_service_account_namespaces=production \
  policies=myapp-policy \
  ttl=1h

# 绑定到多个 Service Account
vault write auth/kubernetes/role/webapp \
  bound_service_account_names="webapp,api-server" \
  bound_service_account_namespaces="production,staging" \
  policies=webapp-policy \
  ttl=1h
```

```yaml
# K8s Deployment 中使用 Vault
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  template:
    spec:
      serviceAccountName: myapp
      containers:
        - name: myapp
          image: myapp:v1.0.0
          env:
            # 使用 Vault Agent 注入
            - name: VAULT_ADDR
              value: "http://vault.vault:8200"
```

#### 3.3 AppRole Auth Method

```bash
# ===== 启用 AppRole 认证 =====
vault auth enable approle

# ===== 创建策略 =====
vault policy write myapp-policy - <<EOF
path "secret/data/myapp/*" {
  capabilities = ["read", "list"]
}
path "database/creds/readonly" {
  capabilities = ["read"]
}
EOF

# ===== 创建 AppRole =====
vault write auth/approle/role/myapp \
  secret_id_ttl=10m \
  token_num_uses=10 \
  token_ttl=20m \
  token_max_ttl=30m \
  secret_id_num_uses=40 \
  policies="myapp-policy"

# ===== 获取 RoleID =====
vault read auth/approle/role/myapp/role-id
# 输出: role_id = abc123-...

# ===== 生成 SecretID =====
vault write -f auth/approle/role/myapp/secret-id
# 输出: secret_id = def456-...

# ===== 使用 RoleID + SecretID 认证 =====
vault write auth/approle/login \
  role_id="abc123-..." \
  secret_id="def456-..."
# 输出: token = s.xyz789-...
```

---

### 4. 策略（Policy）

#### 4.1 Policy 语法

```hcl
# ===== myapp-policy.hcl =====

# 读取应用配置
path "secret/data/myapp/config" {
  capabilities = ["read", "list"]
}

# 读取 API Keys
path "secret/data/myapp/api-keys/*" {
  capabilities = ["read", "list"]
}

# 获取数据库只读凭据
path "database/creds/readonly" {
  capabilities = ["read"]
}

# 获取 TLS 证书
path "pki/issue/myapp" {
  capabilities = ["create", "update"]
}

# 禁止访问管理路径
path "sys/*" {
  capabilities = ["deny"]
}

# 允许 List 子路径
path "secret/metadata/myapp/*" {
  capabilities = ["list"]
}
```

```bash
# 创建策略
vault policy write myapp-policy myapp-policy.hcl

# 查看策略
vault policy read myapp-policy

# 列出所有策略
vault policy list

# 将策略绑定到角色
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=myapp \
  bound_service_account_namespaces=production \
  policies=myapp-policy
```

#### 4.2 策略最佳实践

```
┌─────────────────────────────────────────────────────────────────────┐
│                    策略最佳实践                                       │
│                                                                     │
│  1. 最小权限原则                                                    │
│  ├── 只授予必要的访问权限                                          │
│  ├── 使用 read 而非 write（除非需要）                              │
│  └── 避免使用 sudo 和 root token                                   │
│                                                                     │
│  2. 路径级别控制                                                    │
│  ├── 使用通配符（*）匹配多个路径                                   │
│  ├── 分离读写权限                                                  │
│  └── 使用 template policy 动态路径                                 │
│                                                                     │
│  3. 策略分层                                                        │
│  ├── 基础策略：只读访问公共配置                                    │
│  ├── 应用策略：访问应用特定密钥                                    │
│  ├── 管理策略：管理密钥和策略                                      │
│  └── 管理员策略：完全访问（谨慎使用）                              │
│                                                                     │
│  4. Template Policy（模板策略）                                     │
│  path "secret/data/{{identity.entity.aliases.kubernetes_1.metadata.service_account_namespace}}/*" { │
│    capabilities = ["read"]                                          │
│  }                                                                  │
│  // 根据 Service Account namespace 动态授权                        │
│                                                                     │
│  5. 定期审计                                                        │
│  ├── 定期检查策略是否过时                                          │
│  ├── 移除不再需要的策略                                            │
│  └── 审查策略变更历史                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5. 动态密钥与自动轮换

#### 5.1 动态密钥原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                    动态密钥原理                                       │
│                                                                     │
│  传统静态密钥：                                                      │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                 │
│  │  应用    │─────>│  配置    │─────>│  数据库  │                 │
│  │          │      │  文件    │      │          │                 │
│  └──────────┘      └──────────┘      └──────────┘                 │
│  问题：密码硬编码，轮换困难，泄露风险高                             │
│                                                                     │
│  Vault 动态密钥：                                                    │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌────────┐│
│  │  应用    │─────>│  Vault   │─────>│  数据库  │      │  自动  ││
│  │          │      │          │      │          │      │  过期  ││
│  └──────────┘      └──────────┘      └──────────┘      └────────┘│
│       │                │                   │                       │
│       │   1.请求凭据   │   2.创建用户      │                       │
│       │──────────────>│──────────────────>│                       │
│       │                │                   │                       │
│       │   3.返回凭据   │                   │                       │
│       │<──────────────│                   │                       │
│       │                │                   │                       │
│       │   4.使用凭据连接                  │                       │
│       │──────────────────────────────────>│                       │
│       │                │                   │                       │
│       │                │   5.TTL 到期      │                       │
│       │                │   删除临时用户    │                       │
│       │                │──────────────────>│                       │
│                                                                     │
│  优势：                                                              │
│  ├── 每个应用获取独立的数据库凭据                                  │
│  ├── 凭据自动过期，无需手动轮换                                    │
│  ├── 泄露影响范围小（单个凭据）                                    │
│  └── 完整的审计日志                                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2 自动轮换配置

```bash
# ===== 配置数据库自动轮换 =====

# 启用数据库引擎
vault secrets enable database

# 配置连接（带轮换）
vault write database/config/mydb \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@db.example.com:5432/mydb" \
  allowed_roles="readonly" \
  username="vault_admin" \
  password="admin_password" \
  # 自动轮换配置
  rotation_period="24h" \
  rotation_statements="ALTER ROLE \"{{name}}\" WITH PASSWORD '{{password}}';"

# ===== 配置 Root 凭据轮换 =====
# 轮换 Vault 自身用于连接数据库的 Root 凭据
vault write -force database/rotate-root/mydb
```

#### 5.3 Lease 管理

```bash
# ===== 查看 Lease =====
vault list sys/leases/lookup/database/creds/readonly

# ===== 续约 Lease =====
vault lease renew database/creds/readonly/abc123 1h

# ===== 撤销 Lease =====
vault lease revoke database/creds/readonly/abc123

# ===== 撤销所有 Lease =====
vault lease revoke -prefix database/creds/readonly
```

---

### 6. Kubernetes 集成

#### 6.1 集成方式对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Vault + K8s 集成方式                               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. Vault Agent Sidecar（推荐）                              │   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │  Pod                                                   │ │   │
│  │  │  ┌──────────┐  ┌──────────┐                          │ │   │
│  │  │  │  App     │  │  Vault   │                          │ │   │
│  │  │  │  Container│  │  Agent   │                          │ │   │
│  │  │  │          │  │  Sidecar │                          │ │   │
│  │  │  │  读取文件 │  │  认证    │                          │ │   │
│  │  │  │  ←────────│──│  获取密钥│                          │ │   │
│  │  │  │          │  │  写入文件 │                          │ │   │
│  │  │  └──────────┘  └──────────┘                          │ │   │
│  │  │       │              │                                │ │   │
│  │  │       ▼              ▼                                │ │   │
│  │  │  ┌──────────────────────┐                            │ │   │
│  │  │  │  Shared Volume       │                            │ │   │
│  │  │  │  /vault/secrets/     │                            │ │   │
│  │  │  └──────────────────────┘                            │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │  优点：应用无需修改代码，支持模板渲染                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  2. CSI Secret Store（推荐）                                 │   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │  Pod                                                   │ │   │
│  │  │  ┌──────────┐                                         │ │   │
│  │  │  │  App     │                                         │ │   │
│  │  │  │          │  ← K8s Secret (自动同步)                │ │   │
│  │  │  └──────────┘                                         │ │   │
│  │  │       │                                                │ │   │
│  │  │       ▼                                                │ │   │
│  │  │  ┌──────────────────┐    ┌──────────────────┐        │ │   │
│  │  │  │  SecretProvider  │───>│  Vault CSI       │        │ │   │
│  │  │  │  Class           │    │  Provider        │        │ │   │
│  │  │  └──────────────────┘    └──────────────────┘        │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │  优点：原生 K8s Secret 集成，支持自动轮换                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  3. External Secrets Operator                                │   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │  ExternalSecret ──> External Secrets Operator ──> Vault│ │   │
│  │  │       │                                                  │ │   │
│  │  │       ▼                                                  │ │   │
│  │  │  K8s Secret（自动创建和更新）                            │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │  优点：声明式管理，支持多种后端（Vault/AWS/GCP/Azure）       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  4. Vault SDK 直接集成                                       │   │
│  │  ┌───────────────────────────────────────────────────────┐ │   │
│  │  │  App ──> Vault SDK ──> Vault API                       │ │   │
│  │  └───────────────────────────────────────────────────────┘ │   │
│  │  优点：完全控制，支持复杂场景                               │   │
│  │  缺点：需要修改应用代码                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.2 Vault Agent Sidecar

```yaml
# 使用 Vault Agent Sidecar 注入密钥
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  template:
    metadata:
      annotations:
        # Vault Agent 注入注解
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp"
        # 注入单个密钥
        vault.hashicorp.com/agent-inject-secret-db-credentials: "database/creds/readonly"
        vault.hashicorp.com/agent-inject-template-db-credentials: |
          {{- with secret "database/creds/readonly" -}}
          DB_HOST=db.example.com
          DB_USER={{ .Data.username }}
          DB_PASSWORD={{ .Data.password }}
          {{- end }}
        # 注入多个密钥
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/myapp/config"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/myapp/config" -}}
          API_KEY={{ .Data.data.api_key }}
          SECRET_KEY={{ .Data.data.secret_key }}
          {{- end }}
    spec:
      serviceAccountName: myapp
      containers:
        - name: myapp
          image: myapp:v1.0.0
          env:
            # 使用注入的密钥文件
            - name: DB_CREDENTIALS
              value: /vault/secrets/db-credentials
          volumeMounts:
            - name: vault-secrets
              mountPath: /vault/secrets
              readOnly: true
      volumes:
        - name: vault-secrets
          emptyDir:
            medium: Memory
```

#### 6.3 External Secrets Operator

```bash
# ===== 安装 External Secrets Operator =====
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace
```

```yaml
# ===== 配置 Vault 后端 =====
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: production
spec:
  provider:
    vault:
      server: "http://vault.vault:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "myapp"
          serviceAccountRef:
            name: "myapp"
---
# ===== 创建 ExternalSecret =====
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
  namespace: production
spec:
  refreshInterval: 1h  # 每小时从 Vault 同步
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: myapp-secrets  # 创建的 K8s Secret 名称
    creationPolicy: Owner
  data:
    # 单个字段映射
    - secretKey: db-password
      remoteRef:
        key: secret/data/myapp/config
        property: db_password

    - secretKey: api-key
      remoteRef:
        key: secret/data/myapp/config
        property: api_key

  # 或使用 dataFrom 获取所有字段
  # dataFrom:
  #   - extract:
  #       key: secret/data/myapp/config
```

#### 6.4 CSI Secret Store

```bash
# ===== 安装 Secrets Store CSI Driver =====
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system

# ===== 安装 Vault CSI Provider =====
helm install vault-csi hashicorp/vault-csi-provider \
  --namespace vault
```

```yaml
# ===== SecretProviderClass =====
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: vault-myapp
  namespace: production
spec:
  provider: vault
  parameters:
    roleName: "myapp"
    vaultAddress: "http://vault.vault:8200"
    objects: |
      - objectName: "db-password"
        secretPath: "secret/data/myapp/config"
        secretKey: "db_password"
      - objectName: "api-key"
        secretPath: "secret/data/myapp/config"
        secretKey: "api_key"
  # 可选：同步为 K8s Secret
  secretObjects:
    - secretName: myapp-secrets
      type: Opaque
      data:
        - objectName: db-password
          key: db-password
        - objectName: api-key
          key: api-key
---
# ===== 使用 CSI Volume 的 Deployment =====
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  template:
    spec:
      containers:
        - name: myapp
          image: myapp:v1.0.0
          volumeMounts:
            - name: vault-secrets
              mountPath: /mnt/secrets
              readOnly: true
      volumes:
        - name: vault-secrets
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: "vault-myapp"
```

---

### 7. 审计与合规

#### 7.1 审计日志配置

```bash
# ===== 启用审计日志 =====
# 文件审计
vault audit enable file file_path=/var/log/vault/audit.log

# Syslog 审计
vault audit enable syslog tag="vault" facility="AUTH"

# Socket 审计（发送到日志收集器）
vault audit enable socket address="logger:9090" socket_type="tcp"

# ===== 审计日志格式 =====
# 每条审计日志包含：
# - 请求信息（路径、方法、参数）
# - 响应信息（状态码、数据）
# - 认证信息（Token、Accessor）
# - 时间戳
# - 哈希值（敏感数据脱敏）
```

#### 7.2 审计日志示例

```json
{
  "time": "2026-05-03T10:00:00Z",
  "type": "request",
  "auth": {
    "token_type": "service",
    "accessor": "abc123",
    "display_name": "kubernetes-production-myapp",
    "policies": ["myapp-policy"],
    "metadata": {
      "service_account_name": "myapp",
      "service_account_namespace": "production"
    }
  },
  "request": {
    "id": "def456",
    "operation": "read",
    "path": "secret/data/myapp/config",
    "remote_address": "10.0.0.1"
  },
  "response": {
    "data": {
      "data": {
        "db_password": "hmac-sha256:xxx",
        "api_key": "hmac-sha256:yyy"
      }
    }
  }
}
```

---

### 8. SRE 实战案例

#### 8.1 案例：某金融公司的密钥管理方案

```
┌─────────────────────────────────────────────────────────────────────┐
│              金融公司密钥管理架构                                     │
│                                                                     │
│  需求：                                                              │
│  ├── SOC2 合规要求                                                  │
│  ├── 密钥不能存储在代码/配置文件中                                  │
│  ├── 所有密钥访问必须有审计日志                                     │
│  ├── 数据库凭据必须动态生成                                        │
│  ├── 密钥必须定期轮换                                               │
│  └── 灾难恢复能力                                                   │
│                                                                     │
│  架构：                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Vault HA Cluster (3 节点 Raft)                              │   │
│  │  ├── Auto-Unseal (AWS KMS)                                   │   │
│  │  ├── 审计日志 → ELK                                          │   │
│  │  └── 备份 → S3                                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Secret Engine 配置：                                                │
│  ├── KV v2: 应用配置、API Key                                      │
│  ├── Database: MySQL/PostgreSQL 动态凭据                           │
│  ├── PKI: 内部 TLS 证书                                            │
│  ├── Transit: 敏感数据加密                                         │
│  └── AWS: CI/CD 临时凭据                                           │
│                                                                     │
│  Auth Method 配置：                                                  │
│  ├── Kubernetes: 生产环境 K8s 认证                                 │
│  ├── AppRole: CI/CD 认证                                           │
│  ├── LDAP: 员工访问                                                │
│  └── OIDC: Web UI SSO                                              │
│                                                                     │
│  K8s 集成：                                                          │
│  ├── External Secrets Operator: 声明式管理 K8s Secret              │
│  ├── Vault Agent: 特殊场景的密钥注入                               │
│  └── CSI: 文件挂载方式                                             │
│                                                                     │
│  密钥轮换策略：                                                      │
│  ├── 数据库凭据: 1 小时 TTL，自动轮换                              │
│  ├── API Key: 90 天轮换，ESO 自动同步                              │
│  ├── TLS 证书: 24 小时轮换                                         │
│  └── Root 凭据: 每月手动轮换                                       │
└─────────────────────────────────────────────────────────────────────┘
```

#### 8.2 案例：密钥泄露应急响应

```
┌─────────────────────────────────────────────────────────────────────┐
│              密钥泄露应急响应流程                                     │
│                                                                     │
│  Step 1: 确认泄露范围                                               │
│  ├── 检查审计日志，确认哪些密钥被访问                              │
│  ├── 确认泄露的密钥类型（KV/Database/PKI）                         │
│  └── 确认泄露的时间窗口                                            │
│                                                                     │
│  Step 2: 立即撤销                                                   │
│  ├── 撤销泄露的 Token                                              │
│  │   vault token revoke <token>                                    │
│  ├── 撤销泄露的 Lease                                              │
│  │   vault lease revoke <lease-id>                                 │
│  └── 轮换 Root Token                                               │
│      vault token revoke -self                                      │
│                                                                     │
│  Step 3: 轮换受影响的密钥                                          │
│  ├── 数据库密码: vault write database/rotate-root/mydb             │
│  ├── API Key: 更新并同步到 Vault                                   │
│  ├── TLS 证书: 重新签发                                           │
│  └── 应用密钥: 生成新密钥并更新                                   │
│                                                                     │
│  Step 4: 通知和文档                                                │
│  ├── 通知安全团队                                                  │
│  ├── 通知受影响的应用团队                                          │
│  ├── 记录事件详情                                                  │
│  └── 更新安全事件追踪系统                                          │
│                                                                     │
│  Step 5: 根因分析和改进                                            │
│  ├── 分析泄露原因                                                  │
│  ├── 检查是否有其他类似风险                                        │
│  ├── 更新安全策略                                                  │
│  └── 加强监控告警                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：安装 Vault 并配置 KV Secret Engine

**目标：** 在 K8s 集群安装 Vault，配置 KV 引擎，存储和读取密钥

```bash
# 步骤 1: 安装 Vault（开发模式）
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --namespace vault --create-namespace \
  --set "server.dev.enabled=true" \
  --set "ui.enabled=true"

# 等待就绪
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=vault -n vault --timeout=60s

# 步骤 2: 获取 Root Token
kubectl logs vault-0 -n vault | grep "Root Token"

# 步骤 3: 配置 kubectl port-forward
kubectl port-forward svc/vault -n vault 8200:8200 &

# 步骤 4: 设置环境变量
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root'  # 开发模式 token

# 步骤 5: 启用 KV v2
vault secrets enable -path=secret kv-v2

# 步骤 6: 写入密钥
vault kv put secret/myapp/config \
  db_host="db.example.com" \
  db_password="super-secret" \
  api_key="my-api-key-12345"

# 步骤 7: 读取密钥
vault kv get secret/myapp/config
vault kv get -field=db_password secret/myapp/config

# 步骤 8: 查看版本历史
vault kv metadata get secret/myapp/config
```

### 练习 2：配置 Kubernetes Auth 和 External Secrets Operator

**目标：** 配置 Vault K8s 认证，使用 ESO 自动同步密钥到 K8s Secret

```bash
# 步骤 1: 在 Vault 中启用 K8s 认证
vault auth enable kubernetes
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc"

# 步骤 2: 创建策略
vault policy write myapp-policy - <<EOF
path "secret/data/myapp/*" {
  capabilities = ["read", "list"]
}
EOF

# 步骤 3: 创建 K8s 角色
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=vault-auth \
  bound_service_account_namespaces=production \
  policies=myapp-policy \
  ttl=1h

# 步骤 4: 创建 Service Account
kubectl create namespace production
kubectl create serviceaccount vault-auth -n production

# 步骤 5: 安装 ESO
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace

# 步骤 6: 创建 SecretStore
cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault
  namespace: production
spec:
  provider:
    vault:
      server: "http://vault.vault:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "myapp"
          serviceAccountRef:
            name: "vault-auth"
EOF

# 步骤 7: 创建 ExternalSecret
cat <<EOF | kubectl apply -f -
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: SecretStore
  target:
    name: myapp-secrets
  data:
    - secretKey: db-password
      remoteRef:
        key: secret/data/myapp/config
        property: db_password
    - secretKey: api-key
      remoteRef:
        key: secret/data/myapp/config
        property: api_key
EOF

# 步骤 8: 验证
kubectl get secret myapp-secrets -n production -o jsonpath='{.data.db-password}' | base64 -d
```

### 练习 3：配置 Database 动态密钥

**目标：** 配置 Vault Database 引擎，动态生成 PostgreSQL 凭据

```bash
# 前提：已有 PostgreSQL 实例

# 步骤 1: 启用数据库引擎
vault secrets enable database

# 步骤 2: 配置数据库连接
vault write database/config/postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres.default:5432/mydb" \
  allowed_roles="readonly" \
  username="postgres" \
  password="postgres"

# 步骤 3: 创建角色
vault write database/roles/readonly \
  db_name=postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# 步骤 4: 获取动态凭据
vault read database/creds/readonly

# 输出示例：
# Key                Value
# ---                -----
# lease_id           database/creds/readonly/abc123
# lease_duration     1h
# password           A1b2-C3d4-E5f6
# username           v-token-readonly-abc123

# 步骤 5: 使用凭据连接数据库
psql -h postgres.default -U v-token-readonly-abc123 -d mydb

# 步骤 6: 查看 Lease
vault list sys/leases/lookup/database/creds/readonly

# 步骤 7: 撤销凭据
vault lease revoke database/creds/readonly/abc123
```

---

## 🎯 面试题精选

### 面试题 1：解释 Vault 的核心架构和组件

**答案：**

Vault 由以下核心组件组成：

1. **API Layer**：HTTP/HTTPS 接口，处理客户端请求
2. **Auth Methods**：认证组件，验证客户端身份（Token/LDAP/AWS/K8s/OIDC）
3. **Policies**：策略组件，定义访问权限
4. **Secret Engines**：密钥引擎，生成/存储/管理密钥（KV/Database/PKI/Transit）
5. **Storage Backend**：存储后端，持久化数据（Raft/Consul/S3）
6. **Audit Backend**：审计后端，记录所有操作（File/Syslog/Socket）

核心概念：
- **Seal/Unseal**：Vault 启动后需要 Unseal Key 解封
- **Token**：所有访问的授权单位
- **Lease**：动态密钥的生命周期

### 面试题 2：静态密钥和动态密钥的区别？Vault 如何实现动态密钥？

**答案：**

| 方面 | 静态密钥 | 动态密钥 |
|------|---------|---------|
| 生成方式 | 手动创建 | Vault 自动生成 |
| 生命周期 | 长期有效 | 短期自动过期 |
| 轮换 | 手动轮换 | 自动轮换 |
| 唯一性 | 多应用共享 | 每个应用独立 |
| 审计 | 困难 | 完整审计日志 |

**Vault 动态密钥实现：**
1. 配置 Database Secret Engine 连接到数据库
2. 创建角色定义凭据的权限和 TTL
3. 应用向 Vault 请求凭据
4. Vault 使用管理员账号在数据库中创建临时用户
5. 返回临时凭据给应用
6. TTL 到期后 Vault 自动删除临时用户

### 面试题 3：Vault 与 Kubernetes 有哪些集成方式？各有什么优缺点？

**答案：**

1. **Vault Agent Sidecar**：
   - 优点：应用无需修改代码，支持模板渲染
   - 缺点：增加 Pod 资源开销，文件同步有延迟

2. **External Secrets Operator**：
   - 优点：声明式管理，原生 K8s Secret，支持自动轮换
   - 缺点：需要安装额外组件

3. **CSI Secret Store**：
   - 优点：原生 Volume 挂载，支持自动轮换
   - 缺点：需要安装 CSI Driver

4. **Vault SDK**：
   - 优点：完全控制，支持复杂场景
   - 缺点：需要修改应用代码

**推荐：** External Secrets Operator（声明式管理）+ Vault Agent Sidecar（特殊场景）

### 面试题 4：什么是 Vault 的 Seal/Unseal？生产环境如何处理？

**答案：**

**Seal/Unseal：**
- Vault 启动后处于 Sealed 状态，数据加密不可访问
- 需要提供 Unseal Key 才能解封
- Unseal Key 使用 Shamir's Secret Sharing 算法分片
- 默认需要 5 个 Key 中的 3 个才能解封

**生产环境方案：**
- **Auto-Unseal**：使用 AWS KMS、Azure Key Vault、GCP KMS 自动解封
- **HSM**：使用硬件安全模块存储 Unseal Key
- **Shamir**：分片存储在不同安全位置（不推荐生产）

### 面试题 5：如何设计 Vault 的高可用架构？

**答案：**

1. **Storage Backend**：
   - 使用 Raft 内置 HA（推荐）
   - 或 Consul 集群
   - 跨可用区部署

2. **Vault 集群**：
   - 3+ 节点 Active-Standby
   - 自动故障转移
   - 负载均衡器分发请求

3. **Auto-Unseal**：
   - 使用云 KMS 自动解封
   - 避免手动 Unseal

4. **备份恢复**：
   - 定期快照存储到 S3
   - 跨区域复制
   - 定期恢复测试

5. **监控告警**：
   - Prometheus 指标采集
   - 健康检查告警
   - 审计日志监控

### 面试题 6：Vault 的 Policy 如何工作？如何实现最小权限原则？

**答案：**

**Policy 工作原理：**
- Policy 定义路径级别的访问权限
- 每个 Token 关联一个或多个 Policy
- 请求时 Vault 检查 Token 的 Policy 是否允许该操作

**最小权限原则：**
1. 只授予必要的 capabilities（read/list/create/update/delete）
2. 限制路径范围（使用通配符）
3. 使用 Template Policy 实现动态路径
4. 定期审计和清理过时策略
5. 避免使用 Root Token

### 面试题 7：如何处理密钥泄露事件？

**答案：**

1. **立即响应**：
   - 撤销泄露的 Token/Lease
   - 轮换受影响的密钥
   - 通知安全团队

2. **评估影响**：
   - 检查审计日志确认泄露范围
   - 确认哪些系统受影响

3. **修复措施**：
   - 轮换所有相关密钥
   - 更新受影响的应用配置
   - 检查是否有其他类似风险

4. **改进措施**：
   - 分析泄露原因
   - 更新安全策略
   - 加强监控告警
   - 定期安全培训

### 面试题 8：External Secrets Operator 和 Vault Agent Sidecar 如何选择？

**答案：**

| 方面 | External Secrets Operator | Vault Agent Sidecar |
|------|--------------------------|---------------------|
| 管理方式 | 声明式（CRD） | 注解式 |
| 输出 | K8s Secret | 文件/环境变量 |
| 轮换 | 自动同步 | 需要重启或模板 |
| 适用场景 | 标准 K8s Secret | 文件挂载/模板渲染 |
| 资源开销 | 低（Operator 级别） | 中（每个 Pod 一个 Agent） |

**选择建议：**
- 大多数场景使用 ESO（声明式、标准 K8s Secret）
- 需要文件挂载或模板渲染使用 Vault Agent
- 可以两者结合使用

---

## 📚 深入阅读

1. **Vault 官方文档** - https://developer.hashicorp.com/vault
2. **Vault Architecture** - https://developer.hashicorp.com/vault/docs/internals
3. **External Secrets Operator** - https://external-secrets.io/
4. **Vault CSI Provider** - https://developer.hashicorp.com/vault/docs/platform/k8s/csi
5. **Vault Agent** - https://developer.hashicorp.com/vault/docs/agent
6. **Vault Best Practices** - https://developer.hashicorp.com/vault/docs/secrets/databases
7. **Sealed Secrets** - https://github.com/bitnami-labs/sealed-secrets
8. **SOPS (Secrets OPerationS)** - https://github.com/getsops/sops

---

## ✅ 自检清单

- [ ] 理解 Vault 的核心架构（API/Auth/Policy/Secret Engine/Storage/Audit）
- [ ] 掌握 Seal/Unseal 机制和 Auto-Unseal 配置
- [ ] 能够配置 KV v2 Secret Engine 存储和读取密钥
- [ ] 掌握 Database Secret Engine 动态凭据生成
- [ ] 理解 PKI Engine 证书管理
- [ ] 能够配置 Kubernetes Auth Method
- [ ] 掌握 AppRole Auth Method 用于 CI/CD
- [ ] 理解 Policy 语法和最小权限原则
- [ ] 能够配置 External Secrets Operator 同步密钥
- [ ] 掌握 Vault Agent Sidecar 注入密钥
- [ ] 理解动态密钥和自动轮换机制
- [ ] 能够设计企业级密钥管理方案
