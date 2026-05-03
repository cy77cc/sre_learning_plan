# Day 84: docker-compose 多容器编排

> 📅 日期：2026-05-03
> 📖 学习主题：docker-compose 多容器编排
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 79 (Docker 容器管理), Day 80 (Docker 数据管理), Day 81 (Docker 网络管理), Day 82 (Docker 化 Web 应用)

## 🎯 学习目标

- 掌握 docker-compose.yml 的完整语法与所有核心指令
- 理解服务依赖（depends_on）与健康检查（healthcheck）的配合使用
- 能配置自定义网络、卷挂载和环境变量
- 掌握 profiles 功能实现开发/测试/生产环境差异化
- 理解 extends 和 YAML 锚点实现配置复用
- 能编写生产级 docker-compose 配置

---

## 📖 核心知识点

### 1. Docker Compose 基础

#### 1.1 Compose 的演变

```
Docker Compose 版本演变:

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  docker-compose v1 (Python)                             │
│  ├── 独立二进制: docker-compose                          │
│  ├── version: '3.8'                                    │
│  └── 已停止维护 (2023)                                   │
│                                                         │
│  docker compose v2 (Go)                                 │
│  ├── Docker CLI 插件: docker compose                    │
│  ├── 不再需要 version 字段                              │
│  ├── 支持 profiles                                     │
│  ├── 支持 compose watch                                 │
│  ├── 性能提升 3-5x                                     │
│  └── 当前推荐版本                                       │
│                                                         │
│  关键变化:                                               │
│  v1: docker-compose up -d                               │
│  v2: docker compose up -d                               │
│      (无连字符，作为 docker 子命令)                        │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 Compose 文件结构

```yaml
# docker-compose.yml 完整结构概览
# 注意: v2 不再需要 version 字段

# 服务定义 (核心)
services:
  service-name:
    # 镜像与构建
    image: nginx:1.25
    build:
      context: .
      dockerfile: Dockerfile
      args: {}
      target: production

    # 网络配置
    ports:
      - "8080:80"
    expose:
      - "8080"
    networks:
      - frontend
      - backend

    # 数据卷
    volumes:
      - ./data:/app/data
      - named-volume:/app/logs
      - type: tmpfs
        target: /tmp

    # 环境变量
    environment:
      - KEY=value
    env_file:
      - .env

    # 依赖与启动
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

    # 健康检查
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s

    # 日志配置
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

    # 其他配置
    hostname: my-service
    container_name: my-service
    stdin_open: true
    tty: true
    privileged: false
    cap_add:
      - NET_ADMIN
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
      - /run
    dns:
      - 8.8.8.8
    extra_hosts:
      - "host.docker.internal:host-gateway"
    labels:
      - "com.example.description=My Service"
    profiles:
      - debug

# 网络定义
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
  custom:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1

# 卷定义
volumes:
  db-data:
    driver: local
  app-logs:
    driver: local
    driver_opts:
      type: nfs
      o: addr=10.0.1.100,rw
      device: ":/exports/logs"
```

---

### 2. 服务定义详解

#### 2.1 image 与 build

```yaml
services:
  # 方式 1: 使用现有镜像
  web:
    image: nginx:1.25-alpine

  # 方式 2: 从 Dockerfile 构建
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
      # 指定构建目标 (多阶段构建)
      target: production
      # 构建参数
      args:
        - NODE_ENV=production
        - APP_VERSION=${APP_VERSION:-1.0.0}
      # 构建缓存来源
      cache_from:
        - myapp:latest
      # 给构建的镜像命名
      image: myapp-api:latest
      # 额外的构建标签
      labels:
        - "com.example.version=${APP_VERSION}"

  # 简写形式
  worker:
    build: ./worker
    # 等同于:
    # build:
    #   context: ./worker
    #   dockerfile: Dockerfile

  # 同时指定 image 和 build
  # 构建后自动打上 image 标签
  app:
    build: .
    image: myregistry.example.com/myapp:${VERSION}
    # 适合需要推送到仓库的场景
```

#### 2.2 ports 与 expose

```yaml
services:
  web:
    image: nginx

    # ports: 宿主机:容器 端口映射
    ports:
      # 完整格式
      - "8080:80"
      # 绑定特定 IP
      - "127.0.0.1:8080:80"
      # 长格式
      - target: 80
        published: 8080
        protocol: tcp
        host_ip: 0.0.0.0
      # UDP 端口
      - "5353:53/udp"
      # 同时 TCP 和 UDP
      - target: 5353
        published: 5353
        protocol: udp
      - target: 5353
        published: 5353
        protocol: tcp
      # 随机端口
      - "3000"

  # expose: 仅在 Compose 网络内暴露端口，不映射到宿主机
  internal-api:
    image: myapi:latest
    expose:
      - "8080"
      - "9090"
    # 这些端口只在 docker 网络内可达
```

#### 2.3 environment 与 env_file

```yaml
services:
  app:
    image: myapp:latest

    # 方式 1: 直接定义环境变量
    environment:
      - NODE_ENV=production
      - DB_HOST=mysql
      - DB_PORT=3306
      - LOG_LEVEL=info

    # 方式 2: 映射语法
    environment:
      NODE_ENV: production
      DB_HOST: mysql
      DB_PORT: 3306

    # 方式 3: 从 .env 文件加载
    env_file:
      - .env
      # 可以指定多个文件，后面的覆盖前面的
      - .env.production

    # 方式 4: 可选文件 (不存在时不报错)
    env_file:
      - path: .env.local
        required: false

    # 方式 5: 直接引用宿主机环境变量
    environment:
      - DB_PASSWORD=${DB_PASSWORD}
      - APP_VERSION=${APP_VERSION:-1.0.0}  # 带默认值
```

```bash
# .env 文件 (在 docker-compose.yml 同目录)
# 此文件中的变量会被 docker compose 自动加载
# 也可以在 services 中的变量引用 ${VAR}

# 应用变量
APP_VERSION=2.1.0
APP_ENV=production

# 数据库变量
MYSQL_ROOT_PASSWORD=secure_root_password
DB_PASSWORD=secure_app_password
DB_NAME=myapp

# Redis
REDIS_PASSWORD=secure_redis_password
```

**重要:** `.env` 文件中的变量用于替换 compose 文件中的 `${VAR}`，而 `environment` 中定义的变量才是容器内实际的环境变量。

---

### 3. 服务依赖与健康检查

#### 3.1 depends_on 详解

```yaml
services:
  # 基本依赖 (仅保证启动顺序)
  api:
    image: myapi:latest
    depends_on:
      - mysql
      - redis

  # 带条件的依赖 (推荐生产使用)
  api-v2:
    image: myapi:latest
    depends_on:
      mysql:
        condition: service_healthy      # 等待健康检查通过
        required: true                   # v2.24+: 是否必须
        restart: true                    # v2.24+: 依赖重启时是否重启
      redis:
        condition: service_healthy
      init-db:
        condition: service_completed_successfully  # 等待完成

  # 初始化服务 (运行一次性任务)
  init-db:
    image: myapp:latest
    command: ["python", "manage.py", "migrate"]
    depends_on:
      mysql:
        condition: service_healthy
    # 用完即退出
    restart: "no"

  # 数据库
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # 缓存
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
```

#### 3.2 健康检查配置

```yaml
services:
  # HTTP 健康检查
  web:
    image: nginx
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s      # 检查间隔
      timeout: 5s         # 超时时间
      retries: 3          # 重试次数
      start_period: 40s   # 启动宽限期 (在此期间失败不计入重试)

  # TCP 端口检查
  db:
    image: mysql:8.0
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # Shell 命令检查
  worker:
    image: myworker:latest
    healthcheck:
      test: ["CMD-SHELL", "pgrep -f 'worker' || exit 1"]
      interval: 15s
      timeout: 3s
      retries: 3

  # 禁用健康检查
  debug:
    image: myapp:debug
    healthcheck:
      disable: true

  # 自定义检查脚本
  api:
    image: myapi:latest
    healthcheck:
      test: ["CMD", "/app/healthcheck.sh"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

```
健康检查状态机:

                 ┌─────────────────────┐
                 │     starting        │
                 │  (start_period 内)   │
                 └──────────┬──────────┘
                            │ start_period 结束
                            ▼
                 ┌─────────────────────┐
           ┌─────│     healthy         │◀─────┐
           │     │  (检查成功)          │      │
           │     └──────────┬──────────┘      │
           │                │ 检查失败         │ retries < 3
           │                ▼                  │
           │     ┌─────────────────────┐      │
           │     │     unhealthy       │──────┘
           │     │  (重试中)            │  检查成功
           │     └──────────┬──────────┘
           │                │ retries >= 3
           │                ▼
           │     ┌─────────────────────┐
           └────▶│  container exited   │
                 │  (容器退出)          │
                 └─────────────────────┘

depends_on 行为:
- condition: service_started → 容器启动即可 (不等健康检查)
- condition: service_healthy → 必须 healthy 状态
- condition: service_completed_successfully → 容器正常退出 (exit 0)
```

---

### 4. 网络配置

#### 4.1 默认网络

```yaml
# 不定义 networks 时，Compose 自动创建默认网络
# 网络名: <project-name>_default
# 所有服务都加入此默认网络

services:
  web:
    image: nginx
  api:
    image: myapi:latest
  db:
    image: mysql:8.0
# web, api, db 都在同一个默认网络中
# 可以通过服务名互相访问: web, api, db
```

#### 4.2 自定义网络

```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
    networks:
      - frontend
    depends_on:
      - api

  api:
    image: myapi:latest
    networks:
      - frontend    # 面向 nginx
      - backend     # 面向数据库
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy

  mysql:
    image: mysql:8.0
    networks:
      - backend
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    networks:
      - backend

  # 内部监控服务 (不需要外部访问)
  metrics:
    image: prometheus:latest
    networks:
      - backend
      - monitoring
    profiles:
      - monitoring

networks:
  frontend:
    driver: bridge
    # 驱动选项
    driver_opts:
      com.docker.network.bridge.name: br-frontend

  backend:
    driver: bridge
    internal: true  # 无外部网络访问

  monitoring:
    driver: bridge
    internal: true
    # 自定义子网
    ipam:
      driver: default
      config:
        - subnet: 172.30.0.0/24
          gateway: 172.30.0.1

  # 使用现有网络 (不创建)
  existing-net:
    external: true
    name: my-existing-network

volumes:
  mysql_data:
```

#### 4.3 网络高级配置

```yaml
services:
  app:
    image: myapp:latest
    networks:
      frontend:
        # 指定 IP 地址
        ipv4_address: 172.20.0.100
        # 指定链接本地地址
        link_local_ips:
          - 169.254.100.100
        # 优先级 (值越高优先级越高)
        priority: 1000

      backend:
        ipv4_address: 172.21.0.100

    # 别名 (可从其他服务通过别名访问)
    # 也可以在 networks 内设置
    # networks:
    #   backend:
    #     aliases:
    #       - api-server
    #       - my-api

    # 额外的 hosts 映射
    extra_hosts:
      - "host.docker.internal:host-gateway"
      - "api.local:127.0.0.1"

    # 自定义 DNS
    dns:
      - 8.8.8.8
      - 8.8.4.4
    dns_search:
      - example.com

networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
          gateway: 172.20.0.1
          ip_range: 172.20.0.0/25  # 限制 IP 分配范围

  backend:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.21.0.0/24
```

---

### 5. 数据卷配置

#### 5.1 卷挂载类型

```yaml
services:
  db:
    image: mysql:8.0
    volumes:
      # 命名卷 (持久化, Docker 管理)
      - mysql_data:/var/lib/mysql

      # Bind Mount (宿主机目录)
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro

      # 带选项的 Bind Mount
      - type: bind
        source: ./config/my.cnf
        target: /etc/mysql/conf.d/custom.cnf
        read_only: true
        bind:
          propagation: rslave  # 传播模式

      # tmpfs 挂载 (内存)
      - type: tmpfs
        target: /tmp
        tmpfs:
          size: 100000000  # 100MB
          mode: 1777

  app:
    image: myapp:latest
    volumes:
      # 命名卷
      - app_logs:/app/logs

      # Bind Mount (开发模式)
      - ./src:/app/src:cached  # macOS 优化

      # 只读挂载
      - ./config:/app/config:ro

      # 匿名卷
      - /app/tmp  # Docker 自动管理

      # 带权限的卷
      - type: volume
        source: shared-data
        target: /app/shared
        volume:
          nocopy: true  # 不复制容器内容到卷

  # 配置文件挂载 (只读)
  nginx:
    image: nginx:1.25-alpine
    volumes:
      - type: bind
        source: ./nginx/nginx.conf
        target: /etc/nginx/nginx.conf
        read_only: true
      - type: bind
        source: ./nginx/conf.d
        target: /etc/nginx/conf.d
        read_only: true
      - type: bind
        source: ./certs
        target: /etc/nginx/certs
        read_only: true

volumes:
  mysql_data:
    driver: local
  app_logs:
    driver: local
  shared-data:
    external: true  # 使用已存在的卷
    name: my-shared-data
```

---

### 6. 环境变量管理

#### 6.1 环境变量优先级

```
环境变量优先级 (从高到低):

1. docker compose run -e KEY=value     (命令行)
2. compose 文件中 environment: KEY=value (服务级)
3. compose 文件中 env_file: .env.local  (服务级 env_file)
4. compose 文件所在目录的 .env 文件      (项目级)
5. 宿主机环境变量 export KEY=value     (主机级, 需 ${KEY} 引用)
6. Dockerfile 中 ENV KEY=value         (镜像级)

注意: 变量替换 ${VAR} 在 compose 文件解析时发生
     environment 中的值会传递给容器
```

#### 6.2 变量替换

```yaml
# docker-compose.yml 中的变量替换
services:
  app:
    image: ${APP_IMAGE:-myapp}:${APP_VERSION:-latest}
    ports:
      - "${APP_PORT:-8080}:8080"
    environment:
      - NODE_ENV=${NODE_ENV:-production}
      - DB_HOST=${DB_HOST:-mysql}
      - DB_PASSWORD=${DB_PASSWORD:?Database password is required}
      - APP_NAME=${APP_NAME:-My Application}
    deploy:
      resources:
        limits:
          memory: ${MEMORY_LIMIT:-512M}

# 变量替换语法:
# ${VAR}           - 替换为变量值，未定义则为空
# ${VAR:-default}  - 未定义时使用默认值
# ${VAR:?error}    - 未定义时报错并显示错误信息
# ${VAR:+replace}  - 已定义时使用 replace，否则为空
```

#### 6.3 .env 文件管理最佳实践

```bash
# 项目目录结构:
project/
├── docker-compose.yml          # compose 主文件
├── docker-compose.override.yml # 本地覆盖 (自动加载)
├── docker-compose.prod.yml     # 生产配置
├── .env                        # 项目级变量 (不提交 git)
├── .env.example                # 变量模板 (提交 git)
├── .env.local                  # 本地覆盖 (不提交 git)
└── .gitignore

# .gitignore 内容:
# .env
# .env.local
# .env.production
```

```yaml
# docker-compose.yml - 使用变量
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-app}
    volumes:
      - ${DB_DATA_PATH:-db_data}:/var/lib/mysql

# docker-compose.override.yml - 自动加载的覆盖
# 适用于本地开发
services:
  app:
    build: .
    volumes:
      - ./src:/app/src:cached  # 热重载
    environment:
      - NODE_ENV=development
      - DEBUG=*

# docker-compose.prod.yml - 生产环境
services:
  app:
    image: myregistry.example.com/myapp:${APP_VERSION}
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
```

---

### 7. Profiles

#### 7.1 Profiles 概念

```yaml
# Profiles 允许按需启动服务子集
# 未设置 profiles 的服务始终启动
# 设置了 profiles 的服务只在指定 profile 激活时启动

services:
  # 始终启动的核心服务
  app:
    image: myapp:latest
    profiles: []  # 空列表 = 始终启动

  db:
    image: mysql:8.0
    # 不设置 profiles = 始终启动

  redis:
    image: redis:7-alpine
    # 不设置 profiles

  # 仅调试时启动
  debug-tools:
    image: busybox
    profiles:
      - debug
    command: sleep infinity

  # 仅监控时启动
  prometheus:
    image: prometheus:latest
    profiles:
      - monitoring

  grafana:
    image: grafana:latest
    profiles:
      - monitoring

  # 测试专用
  test-db:
    image: mysql:8.0
    profiles:
      - test
    environment:
      MYSQL_DATABASE: test_db

  # 开发工具
  adminer:
    image: adminer:latest
    profiles:
      - dev
    ports:
      - "8080:8080"

  mailhog:
    image: mailhog/mailhog:latest
    profiles:
      - dev
    ports:
      - "1025:1025"
      - "8025:8025"
```

```bash
# 使用 profiles

# 默认启动: 只启动 app, db, redis (没有 profiles 的服务)
docker compose up -d

# 启动调试工具
docker compose --profile debug up -d

# 启动监控服务
docker compose --profile monitoring up -d

# 启动多个 profiles
docker compose --profile dev --profile debug up -d

# 启动所有 profiles
docker compose --profile dev --profile debug --profile monitoring up -d

# 指定服务启动 (忽略 profiles)
docker compose up -d app db  # 只启动指定服务

# 使用 COMPOSE_PROFILES 环境变量
export COMPOSE_PROFILES=debug,monitoring
docker compose up -d
```

---

### 8. extends 与 YAML 锚点

#### 8.1 YAML 锚点和合并

```yaml
# YAML 锚点: &anchor 定义, *anchor 引用, << 合并映射

# 定义通用模板
x-common-env: &common-env
  TZ: Asia/Shanghai
  LANG: C.UTF-8
  LOG_FORMAT: json

x-db-env: &db-env
  <<: *common-env
  DB_HOST: mysql
  DB_PORT: 3306

x-redis-env: &redis-env
  <<: *common-env
  REDIS_HOST: redis
  REDIS_PORT: 6379

x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"

x-healthcheck-defaults: &healthcheck-defaults
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 30s

x-deploy-defaults: &deploy-defaults
  restart: unless-stopped
  logging: *default-logging

services:
  api:
    <<: *deploy-defaults
    image: myapi:latest
    environment:
      <<: [*db-env, *redis-env]  # 合并多个锚点
      APP_NAME: API Service
      APP_PORT: "8080"

  worker:
    <<: *deploy-defaults
    image: myworker:latest
    environment:
      <<: [*db-env, *redis-env]
      WORKER_CONCURRENCY: "4"

  scheduler:
    <<: *deploy-defaults
    image: myscheduler:latest
    environment:
      <<: *db-env
      SCHEDULE_CRON: "0 */6 * * *"
```

#### 8.2 extends 关键字

```yaml
# base-services.yml (基础配置文件)
services:
  base-app:
    image: myapp:latest
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

# docker-compose.yml (使用 extends)
services:
  api:
    extends:
      file: base-services.yml
      service: base-app
    environment:
      - SERVICE_TYPE=api
    ports:
      - "8080:8080"
    networks:
      - frontend
      - backend

  admin:
    extends:
      file: base-services.yml
      service: base-app
    environment:
      - SERVICE_TYPE=admin
    ports:
      - "8081:8080"
    networks:
      - frontend
      - backend
    profiles:
      - admin
```

**extends vs YAML 锚点:**
| 特性 | extends | YAML 锚点 |
|------|---------|----------|
| 跨文件引用 | 支持 | 不支持 (同一文件内) |
| 覆盖配置 | 支持深度合并 | 手动合并 |
| networks/volumes | 不继承 | 自然继承 |
| depends_on | 不继承 | 自然继承 |
| 灵活性 | 中 | 高 |

---

### 9. 扩展与部署

#### 9.1 服务扩展 (Scale)

```yaml
services:
  worker:
    image: myworker:latest
    command: ["python", "worker.py"]
    deploy:
      replicas: 3  # Swarm 模式下的副本数
    # 非 Swarm 模式使用 docker compose up --scale

  api:
    image: myapi:latest
    ports:
      # 注意: 多副本时不能绑定固定宿主机端口
      # 使用随机端口或不映射
      - "8080"
    deploy:
      replicas: 2
```

```bash
# 非 Swarm 模式下扩展
docker compose up -d --scale worker=3 --scale api=2

# 查看扩展后的容器
docker compose ps
# worker-1  ...  Up
# worker-2  ...  Up
# worker-3  ...  Up
# api-1     ...  Up
# api-2     ...  Up

# 注意事项:
# 1. 端口映射需要使用随机端口
# 2. container_name 不能用于多副本
# 3. 需要负载均衡器分发请求
```

#### 9.2 资源限制

```yaml
services:
  app:
    image: myapp:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'       # 最多使用 2 核
          memory: 1G         # 最多使用 1GB 内存
          pids: 100          # 最多 100 个进程
        reservations:
          cpus: '0.5'       # 至少保留 0.5 核
          memory: 256M       # 至少保留 256MB

    # ulimits 配置
    ulimits:
      nproc: 65535          # 最大进程数
      nofile:
        soft: 65535         # 文件描述符软限制
        hard: 65535         # 文件描述符硬限制
      memlock:
        soft: -1            # 内存锁定不限制
        hard: -1

    # OOM 配置
    oom_kill_disable: false  # 默认: 允许 OOM killer
    oom_score_adj: 500       # OOM 优先级 (-1000 到 1000)
```

---

### 10. 生产级配置示例

#### 10.1 完整的 Web 应用生产配置

```yaml
# docker-compose.prod.yml
# 使用: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  # === 反向代理 ===
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      app:
        condition: service_healthy
    networks:
      - frontend
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # === 应用服务 ===
  app:
    image: ${REGISTRY:-ghcr.io/myorg}/myapp:${APP_VERSION:?APP_VERSION is required}
    environment:
      - APP_ENV=production
      - APP_DEBUG=false
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-app}
      - DB_USER=${DB_USER:-app}
      - DB_PASSWORD=${DB_PASSWORD:?DB_PASSWORD is required}
      - REDIS_URL=redis://:${REDIS_PASSWORD:?REDIS_PASSWORD is required}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required}
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - frontend
      - backend
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8080/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true

  # === Worker 进程 ===
  worker:
    image: ${REGISTRY:-ghcr.io/myorg}/myapp:${APP_VERSION}
    command: ["python", "worker.py"]
    environment:
      - APP_ENV=production
      - DB_HOST=mysql
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-4}
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
      replicas: ${WORKER_REPLICAS:-2}
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
    cap_drop:
      - ALL

  # === 数据库 ===
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required}
      MYSQL_DATABASE: ${DB_NAME:-app}
      MYSQL_USER: ${DB_USER:-app}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/conf.d:/etc/mysql/conf.d:ro
      - ./mysql/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    networks:
      - backend
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

  # === 缓存 ===
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
      --save 900 1
      --save 300 10
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 768M
        reservations:
          memory: 256M
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # === 数据库备份 (定时任务) ===
  db-backup:
    image: mysql:8.0
    command: >
      sh -c '
        while true; do
          echo "Starting backup at $$(date)";
          mysqldump -h mysql -u root -p$${MYSQL_ROOT_PASSWORD} --all-databases --single-transaction \
            | gzip > /backup/dump_$$(date +%Y%m%d_%H%M%S).sql.gz;
          echo "Backup completed at $$(date)";
          find /backup -name "dump_*.sql.gz" -mtime +7 -delete;
          sleep 86400;
        done
      '
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - db_backup:/backup
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - backend
    restart: always
    profiles:
      - backup
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local
  nginx_cache:
    driver: local
  db_backup:
    driver: local
```

---

## 💻 实战练习

### 练习 1: 基础多服务编排

**目标:** 使用 docker-compose 部署 WordPress + MySQL。

```yaml
# docker-compose.yml
services:
  wordpress:
    image: wordpress:6-php8.2-apache
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_HOST: mysql
      WORDPRESS_DB_NAME: wordpress
      WORDPRESS_DB_USER: wp_user
      WORDPRESS_DB_PASSWORD: wp_password
    volumes:
      - wordpress_data:/var/www/html
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wp_user
      MYSQL_PASSWORD: wp_password
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped

volumes:
  wordpress_data:
  mysql_data:
```

```bash
# 部署
docker compose up -d

# 验证
docker compose ps
docker compose logs -f wordpress

# 访问 http://localhost:8080 完成安装

# 清理
docker compose down -v
```

### 练习 2: 使用 Profiles 管理多环境

**目标:** 创建一个支持开发、测试、生产三种环境的 compose 配置。

```bash
# 任务:
# 1. 基础服务 (app, db, redis) 无 profiles，始终启动
# 2. dev profile: adminer (数据库管理), mailhog (邮件测试)
# 3. test profile: test-db (测试数据库), selenium
# 4. monitoring profile: prometheus, grafana

# 使用方式:
docker compose up -d                              # 仅基础服务
docker compose --profile dev up -d                # 基础 + 开发工具
docker compose --profile monitoring up -d         # 基础 + 监控
docker compose --profile dev --profile test up -d # 全部
```

### 练习 3: 生产级配置与故障排查

**目标:** 部署一个包含故意错误的生产级环境，练习排查。

```bash
# 创建包含以下问题的环境:
# 1. 环境变量缺失 (DB_PASSWORD 未定义)
# 2. 服务启动顺序问题 (app 在 db 就绪前启动)
# 3. 端口冲突 (两个服务绑定同一端口)
# 4. 卷权限问题 (挂载目录权限不正确)
# 5. 网络配置错误 (服务在不同网络)

# 排查任务:
docker compose config          # 检查配置语法
docker compose up -d           # 观察启动错误
docker compose logs app        # 查看错误日志
docker compose ps              # 查看服务状态

# 逐个修复问题并验证
```

---

## 🎯 面试题精选

### 1. docker-compose 中 depends_on 和 healthcheck 如何配合使用？

**参考答案:**

默认的 `depends_on` 只保证容器启动顺序，不保证服务就绪。例如 MySQL 容器启动后还需要初始化数据库，此时连接可能失败。

解决方案: 使用 `condition: service_healthy`，配合 `healthcheck` 定义的健康检查命令:

```yaml
depends_on:
  mysql:
    condition: service_healthy
```

`healthcheck` 的 `start_period` 参数很关键，它定义了启动宽限期内的失败不计入重试次数。

### 2. docker-compose 的 profiles 有什么用？

**参考答案:**

Profiles 允许将服务分组按需启动。没有设置 profiles 的服务始终启动，设置了 profiles 的服务只在 `--profile` 激活时启动。

典型场景:
- `dev` profile: 包含开发工具（adminer, mailhog）
- `test` profile: 包含测试服务（test-db, selenium）
- `monitoring` profile: 包含监控服务（prometheus, grafana）
- `debug` profile: 包含调试工具（busybox, strace）

### 3. 如何在 docker-compose 中实现配置复用？

**参考答案:**

两种主要方式:
1. **YAML 锚点**: 使用 `&anchor` 定义、`*anchor` 引用、`<<` 合并映射。在同一文件内复用配置。
2. **extends**: 使用 `extends` 关键字从其他文件继承服务配置。支持跨文件复用。

推荐: 简单场景用 YAML 锚点，复杂场景用 extends。避免过度抽象导致配置难以理解。

### 4. docker-compose.yml 中 environment 和 env_file 有什么区别？

**参考答案:**

- **environment**: 在 compose 文件中直接定义环境变量，适合少量固定配置
- **env_file**: 从外部文件加载环境变量，适合大量变量或敏感信息

优先级: `environment` > `env_file`。两者可以同时使用，`environment` 中的同名变量会覆盖 `env_file` 中的值。

注意: `.env` 文件是 compose 文件级的变量替换，不是容器的环境变量。

### 5. 如何在 docker-compose 中实现零停机更新？

**参考答案:**

在非 Swarm 模式下:
1. 构建新镜像: `docker compose build`
2. 更新服务: `docker compose up -d --no-deps --build <service>`
3. Compose 会自动停止旧容器、启动新容器

在 Swarm 模式下:
1. 使用 `deploy.update_config` 配置滚动更新策略
2. `parallelism`: 同时更新的容器数
3. `delay`: 每批更新之间的等待时间
4. `order`: `start-first` (先启动新容器再停止旧) 或 `stop-first`

### 6. docker-compose 中 internal: true 的网络有什么特性？

**参考答案:**

`internal: true` 创建的网络只允许容器间通信，禁止容器访问外部网络（包括互联网）。这通过不配置 NAT 和网关实现。

适用场景:
- 数据库网络（不应直接暴露到互联网）
- 内部微服务通信
- 缓存层网络

如果 internal 网络中的容器需要访问外部，可以同时加入另一个非 internal 网络。

### 7. 如何管理 docker-compose 中的敏感信息？

**参考答案:**

1. **.env 文件**: 将密码放入 `.env`，通过 `${VAR}` 引用，确保 `.env` 在 `.gitignore` 中
2. **Docker secrets** (Swarm 模式): 使用 `secrets` 关键字，挂载到 `/run/secrets/`
3. **外部密钥管理**: 使用 HashiCorp Vault 等，应用启动时从 Vault 读取密码
4. **环境变量注入**: 运行时从 CI/CD 系统注入

禁止: 在 docker-compose.yml 中硬编码密码。

### 8. docker-compose.override.yml 的作用是什么？

**参考答案:**

`docker-compose.override.yml` 会在 `docker compose up` 时自动加载，用于覆盖 `docker-compose.yml` 中的配置。

典型用途: 开发环境覆盖（挂载源码目录、开启调试模式、暴露额外端口）。

使用 `-f` 指定其他文件时不自动加载:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 9. 如何在 docker-compose 中配置日志轮转？

**参考答案:**

```yaml
services:
  app:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

`max-size`: 单个日志文件最大大小
`max-file`: 最多保留的日志文件数

可以在 daemon.json 中设置全局默认值:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 10. docker compose up 和 docker compose create + start 有什么区别？

**参考答案:**

- `docker compose up`: 创建并启动容器，如果容器已存在则重建（如果配置变化）
- `docker compose create`: 仅创建容器，不启动
- `docker compose start`: 启动已创建的容器
- `docker compose up -d`: 后台运行
- `docker compose up --build`: 强制重新构建镜像
- `docker compose up --force-recreate`: 强制重新创建容器

---

## 📚 深入阅读

- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [Compose 文件规范](https://docs.docker.com/reference/compose-file/)
- [Compose Profiles](https://docs.docker.com/compose/how-tos/profiles/)
- [Compose 环境变量](https://docs.docker.com/compose/how-tos/environment-variables/)
- [Compose 生产最佳实践](https://docs.docker.com/compose/how-tos/production/)
- [Compose Watch (开发模式)](https://docs.docker.com/compose/how-tos/use-profiles/)

---

## ✅ 自检清单

- [ ] 理解 docker-compose.yml 的完整语法结构
- [ ] 掌握 depends_on 与 healthcheck 的配合使用
- [ ] 能配置自定义网络（bridge、internal、自定义子网）
- [ ] 能管理数据卷（命名卷、bind mount、tmpfs）
- [ ] 理解环境变量的优先级和 .env 文件管理
- [ ] 能使用 profiles 管理不同环境的配置
- [ ] 掌握 YAML 锚点和 extends 实现配置复用
- [ ] 能配置资源限制（CPU、内存、ulimits）
- [ ] 能编写生产级 docker-compose 配置
- [ ] 理解 docker compose 的常用命令和生命周期
- [ ] 能排查 compose 编排中的常见问题
