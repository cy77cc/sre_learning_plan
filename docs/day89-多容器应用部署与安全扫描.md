# Day 89: 多容器应用部署与安全扫描

> 📅 日期：2026-05-03
> 📖 学习主题：LAMP/LNMP 完整部署、微服务架构、Trivy/Grype 安全扫描、CI/CD 集成、生产检查清单
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 80-88 Docker 全部内容

---

## 🎯 学习目标

- 能够使用 Docker Compose 部署完整的 LAMP/LNMP 应用栈
- 理解微服务架构的容器化部署模式
- 掌握 Trivy 和 Grype 安全扫描工具
- 能够在 CI/CD 流水线中集成容器安全扫描
- 掌握生产环境容器部署检查清单

---

## 📖 核心知识点

### 1. LAMP/LNMP 完整部署

#### 1.1 LAMP 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    LAMP 容器架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   外部请求                                                   │
│      │                                                      │
│      ▼                                                      │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                 Nginx / Apache                        │ │
│   │                 (Web 服务器)                          │ │
│   │                 Port: 80, 443                         │ │
│   └──────────────┬───────────────────────────────────────┘ │
│                  │                                          │
│                  ▼                                          │
│   ┌──────────────────────────────────────────────────────┐ │
│   │              PHP-FPM / Python / Node.js               │ │
│   │              (应用运行时)                              │ │
│   │              Port: 9000 / 8000 / 3000                │ │
│   └──────────────┬───────────────────────────────────────┘ │
│                  │                                          │
│          ┌───────┼───────┐                                  │
│          ▼       ▼       ▼                                  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│   │  MySQL   │ │  Redis   │ │  MinIO   │                  │
│   │ (数据库) │ │ (缓存)   │ │ (存储)   │                  │
│   │ 3306     │ │ 6379     │ │ 9000     │                  │
│   └──────────┘ └──────────┘ └──────────┘                  │
│                                                             │
│   Docker 网络                                              │
│   ┌──────────────────────────────────────────────────────┐ │
│   │  frontend-net (Nginx <-> PHP)                        │ │
│   │  backend-net  (PHP <-> MySQL/Redis)                  │ │
│   │  db-net       (MySQL 独立网络)                       │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 LAMP 完整 Docker Compose 配置

```yaml
# docker-compose.lamp.yml
version: '3.8'

services:
  # ============ Web 服务器 ============
  nginx:
    image: nginx:1.25-alpine
    container_name: lamp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - app-code:/var/www/html
      - nginx-logs:/var/log/nginx
    depends_on:
      - php
    networks:
      - frontend
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ============ PHP 应用 ============
  php:
    build:
      context: ./php
      dockerfile: Dockerfile
    container_name: lamp-php
    restart: unless-stopped
    volumes:
      - app-code:/var/www/html
      - ./php/uploads.ini:/usr/local/etc/php/conf.d/uploads.ini:ro
    environment:
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_DATABASE=appdb
      - DB_USERNAME=appuser
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    secrets:
      - db_password
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - frontend
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    healthcheck:
      test: ["CMD-SHELL", "php-fpm-healthcheck || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ============ MySQL 数据库 ============
  mysql:
    image: mysql:8.0
    container_name: lamp-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password
      - MYSQL_DATABASE=appdb
      - MYSQL_USER=appuser
      - MYSQL_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - mysql_root_password
      - db_password
    volumes:
      - mysql-data:/var/lib/mysql
      - ./mysql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
      - ./mysql/my.cnf:/etc/mysql/conf.d/custom.cnf:ro
    networks:
      - backend
      - db
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============ Redis 缓存 ============
  redis:
    image: redis:7-alpine
    container_name: lamp-redis
    restart: unless-stopped
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis-data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============ phpMyAdmin（可选） ============
  phpmyadmin:
    image: phpmyadmin:latest
    container_name: lamp-phpmyadmin
    restart: unless-stopped
    environment:
      - PMA_HOST=mysql
      - PMA_PORT=3306
      - MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password
    secrets:
      - mysql_root_password
    ports:
      - "8080:80"
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - db
    profiles:
      - debug

# ============ 数据卷 ============
volumes:
  app-code:
    driver: local
  mysql-data:
    driver: local
  redis-data:
    driver: local
  nginx-logs:
    driver: local

# ============ 网络 ============
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 不允许外部访问
  db:
    driver: bridge
    internal: true

# ============ 密钥 ============
secrets:
  db_password:
    file: ./secrets/db_password.txt
  mysql_root_password:
    file: ./secrets/mysql_root_password.txt
```

#### 1.3 Nginx 配置

```nginx
# nginx/conf.d/default.conf
upstream php-fpm {
    server php:9000;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    root /var/www/html/public;
    index index.php index.html;

    # SSL 配置
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 健康检查
    location /health {
        access_log off;
        return 200 "OK\n";
    }

    # PHP 处理
    location ~ \.php$ {
        fastcgi_pass php-fpm;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;

        # 安全：防止路径遍历
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
    }

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }

    # 健康检查端点
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;
}
```

#### 1.4 PHP Dockerfile

```dockerfile
# php/Dockerfile
FROM php:8.2-fpm-alpine

# 安装系统依赖
RUN apk add --no-cache \
    freetype-dev \
    libjpeg-turbo-dev \
    libpng-dev \
    libzip-dev \
    icu-dev \
    oniguruma-dev \
    $PHPIZE_DEPS

# 安装 PHP 扩展
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
    gd \
    pdo \
    pdo_mysql \
    mysqli \
    mbstring \
    zip \
    intl \
    opcache \
    bcmath

# 安装 Redis 扩展
RUN pecl install redis && docker-php-ext-enable redis

# 安装 Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# 安装 PHP-FPM 健康检查
RUN wget -O /usr/local/bin/php-fpm-healthcheck \
    https://raw.githubusercontent.com/renatomefi/php-fpm-healthcheck/master/php-fpm-healthcheck \
    && chmod +x /usr/local/bin/php-fpm-healthcheck

# PHP 配置
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

# 创建应用用户
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

# 设置工作目录
WORKDIR /var/www/html

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 安装依赖
RUN composer install --no-dev --optimize-autoloader --no-interaction

# 设置权限
RUN chown -R appuser:appgroup /var/www/html/storage /var/www/html/bootstrap/cache

USER appuser

EXPOSE 9000

CMD ["php-fpm"]
```

#### 1.5 数据库初始化脚本

```sql
-- mysql/init.sql
CREATE DATABASE IF NOT EXISTS appdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE appdb;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS posts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    status ENUM('draft', 'published', 'archived') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建只读用户（最小权限原则）
CREATE USER IF NOT EXISTS 'app_readonly'@'%' IDENTIFIED BY 'readonly_password';
GRANT SELECT ON appdb.* TO 'app_readonly'@'%';
FLUSH PRIVILEGES;
```

#### 1.6 Redis 配置

```conf
# redis/redis.conf
# 网络
bind 0.0.0.0
port 6379
protected-mode yes
requirepass your_redis_password

# 内存
maxmemory 128mb
maxmemory-policy allkeys-lru

# 持久化
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000

# 安全
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG "CONFIG_b82a3f"

# 日志
loglevel notice
logfile ""
```

#### 1.7 LNMP 与 LAMP 的区别

```
┌─────────────────────────────────────────────────────────────┐
│                LAMP vs LNMP 对比                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   LAMP:                                                     │
│   Apache (mod_php) ─→ PHP ─→ MySQL                          │
│   - Apache 处理 PHP 请求                                    │
│   - mod_php 嵌入 Apache 进程                                │
│   - 配置简单，适合传统 PHP 应用                             │
│                                                             │
│   LNMP:                                                     │
│   Nginx (FastCGI) ─→ PHP-FPM ─→ MySQL                      │
│   - Nginx 反向代理到 PHP-FPM                                │
│   - PHP-FPM 独立进程池                                      │
│   - 高并发性能更好，内存占用更低                             │
│   - 适合现代 PHP 应用（Laravel、WordPress）                 │
│                                                             │
│   性能对比：                                                 │
│   ┌──────────────┬───────────────┬──────────────────┐      │
│   │ 场景         │ Apache+mod_php│ Nginx+PHP-FPM    │      │
│   ├──────────────┼───────────────┼──────────────────┤      │
│   │ 静态文件     │ 中等          │ 优秀             │      │
│   │ 高并发       │ 较差          │ 优秀             │      │
│   │ 内存占用     │ 高            │ 低               │      │
│   │ 配置复杂度   │ 简单          │ 中等             │      │
│   └──────────────┴───────────────┴──────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. 微服务架构容器化

#### 2.1 微服务架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                微服务架构容器化                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   外部请求                                                   │
│      │                                                      │
│      ▼                                                      │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                 API Gateway                           │ │
│   │              (Nginx/Kong/Traefik)                     │ │
│   │                 Port: 80/443                          │ │
│   └──────────────────────┬───────────────────────────────┘ │
│                          │                                  │
│          ┌───────────────┼───────────────┐                 │
│          ▼               ▼               ▼                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│   │ 用户服务 │    │ 订单服务 │    │ 商品服务 │            │
│   │ user-svc │    │ order-svc│    │ product- │            │
│   │ :3001    │    │ :3002    │    │ svc:3003 │            │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘            │
│        │               │               │                   │
│        └───────────────┼───────────────┘                   │
│                        ▼                                   │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                 Message Queue                         │ │
│   │              (RabbitMQ / Kafka)                        │ │
│   └──────────────────────────────────────────────────────┘ │
│                        │                                   │
│          ┌─────────────┼─────────────┐                    │
│          ▼             ▼             ▼                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│   │  MySQL   │  │  Redis   │  │ MongoDB  │               │
│   │ (用户库) │  │ (缓存)   │  │ (日志)   │               │
│   └──────────┘  └──────────┘  └──────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 微服务 Docker Compose 部署

```yaml
# docker-compose.microservices.yml
version: '3.8'

services:
  # ============ API Gateway ============
  gateway:
    image: nginx:1.25-alpine
    container_name: gateway
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./gateway/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - user-service
      - order-service
      - product-service
    networks:
      - frontend
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'

  # ============ 用户服务 ============
  user-service:
    build:
      context: ./services/user-service
      dockerfile: Dockerfile
    container_name: user-service
    restart: unless-stopped
    environment:
      - SERVICE_NAME=user-service
      - DB_HOST=user-db
      - DB_PORT=3306
      - DB_NAME=users
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
    secrets:
      - jwt_secret
    depends_on:
      user-db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - frontend
      - backend
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

  # ============ 订单服务 ============
  order-service:
    build:
      context: ./services/order-service
      dockerfile: Dockerfile
    container_name: order-service
    restart: unless-stopped
    environment:
      - SERVICE_NAME=order-service
      - DB_HOST=order-db
      - DB_PORT=5432
      - DB_NAME=orders
      - USER_SERVICE_URL=http://user-service:3001
      - PRODUCT_SERVICE_URL=http://product-service:3003
      - RABBITMQ_URL=amqp://rabbitmq:5672
    depends_on:
      order-db:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - frontend
      - backend
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

  # ============ 商品服务 ============
  product-service:
    build:
      context: ./services/product-service
      dockerfile: Dockerfile
    container_name: product-service
    restart: unless-stopped
    environment:
      - SERVICE_NAME=product-service
      - MONGO_URL=mongodb://mongo:27017/products
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      mongo:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - frontend
      - backend
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

  # ============ 用户数据库 ============
  user-db:
    image: mysql:8.0
    container_name: user-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_pw
      - MYSQL_DATABASE=users
      - MYSQL_USER=app
      - MYSQL_PASSWORD_FILE=/run/secrets/mysql_app_pw
    secrets:
      - mysql_root_pw
      - mysql_app_pw
    volumes:
      - user-db-data:/var/lib/mysql
    networks:
      - backend
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============ 订单数据库 ============
  order-db:
    image: postgres:16-alpine
    container_name: order-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=orders
      - POSTGRES_USER=app
      - POSTGRES_PASSWORD_FILE=/run/secrets/pg_app_pw
    secrets:
      - pg_app_pw
    volumes:
      - order-db-data:/var/lib/postgresql/data
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============ 商品数据库 ============
  mongo:
    image: mongo:7
    container_name: product-db
    restart: unless-stopped
    environment:
      - MONGO_INITDB_ROOT_USERNAME=app
      - MONGO_INITDB_ROOT_PASSWORD_FILE=/run/secrets/mongo_app_pw
    secrets:
      - mongo_app_pw
    volumes:
      - mongo-data:/data/db
    networks:
      - backend
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============ Redis ============
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    command: redis-server --requirepass redis_password --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis_password", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============ RabbitMQ ============
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: rabbitmq
    restart: unless-stopped
    environment:
      - RABBITMQ_DEFAULT_USER=app
      - RABBITMQ_DEFAULT_PASS_FILE=/run/secrets/rabbitmq_pw
    secrets:
      - rabbitmq_pw
    ports:
      - "15672:15672"  # 管理界面（仅开发环境）
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    networks:
      - backend
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============ 日志收集 ============
  fluentd:
    image: fluent/fluentd:v1.16
    container_name: fluentd
    restart: unless-stopped
    volumes:
      - ./fluentd/conf:/fluentd/etc:ro
      - fluentd-data:/fluentd/log
    ports:
      - "24224:24224"
      - "24224:24224/udp"
    networks:
      - backend

volumes:
  user-db-data:
  order-db-data:
  mongo-data:
  redis-data:
  rabbitmq-data:
  fluentd-data:

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  mysql_root_pw:
    file: ./secrets/mysql_root_pw.txt
  mysql_app_pw:
    file: ./secrets/mysql_app_pw.txt
  pg_app_pw:
    file: ./secrets/pg_app_pw.txt
  mongo_app_pw:
    file: ./secrets/mongo_app_pw.txt
  rabbitmq_pw:
    file: ./secrets/rabbitmq_pw.txt
```

#### 2.3 微服务 Dockerfile 模板

```dockerfile
# services/user-service/Dockerfile

# ===== 构建阶段 =====
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY . .
RUN npm run build

# ===== 运行阶段 =====
FROM node:18-alpine
RUN apk add --no-cache dumb-init curl
RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

USER appuser
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3001/health || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/main.js"]
```

#### 2.4 服务间通信模式

```
┌─────────────────────────────────────────────────────────────┐
│              微服务间通信模式                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 同步通信（HTTP/gRPC）                                   │
│   ┌──────────┐    HTTP Request    ┌──────────┐            │
│   │ Service A│ ─────────────────→ │ Service B│            │
│   │          │ ←───────────────── │          │            │
│   └──────────┘    HTTP Response   └──────────┘            │
│   特点：简单直观，但有耦合性和延迟                           │
│                                                             │
│   2. 异步通信（消息队列）                                    │
│   ┌──────────┐    Publish     ┌──────────┐   Consume     │
│   │ Service A│ ─────────────→ │  Queue   │ ────────────→ │
│   └──────────┘                │(RabbitMQ)│   Service B   │
│                               └──────────┘                │
│   特点：解耦、削峰、可靠，但增加复杂度                       │
│                                                             │
│   3. 服务发现                                               │
│   - Docker Compose：使用服务名（如 http://user-service:3001）│
│   - Kubernetes：使用 Service 名称                          │
│   - Consul/etcd：外部服务注册中心                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. 容器安全扫描

#### 3.1 Trivy 安全扫描

Trivy 是最流行的容器安全扫描工具，支持镜像、文件系统、Git 仓库等多种扫描目标。

```bash
# 1. 安装 Trivy
# Ubuntu/Debian
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# 使用 Docker
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image nginx:latest

# 2. 扫描镜像漏洞
trivy image nginx:latest

# 输出示例：
# nginx:latest (debian 12.4)
# Total: 156 (UNKNOWN: 0, LOW: 85, MEDIUM: 52, HIGH: 17, CRITICAL: 2)
#
# ┌──────────────┬────────────────┬──────────┬─────────────────────────────────┐
# │   Library    │ Vulnerability  │ Severity │         Fixed Version           │
# ├──────────────┼────────────────┼──────────┼─────────────────────────────────┤
# │ libssl3      │ CVE-2024-0727  │ HIGH     │ 3.0.13-1~deb12u1                │
# │ openssl      │ CVE-2024-0727  │ HIGH     │ 3.0.13-1~deb12u1                │
# └──────────────┴────────────────┴──────────┴─────────────────────────────────┘

# 3. 只显示高危和严重漏洞
trivy image --severity HIGH,CRITICAL nginx:latest

# 4. 输出 JSON 格式
trivy image --format json -o report.json nginx:latest

# 5. 输出 SARIF 格式（GitHub Security 集成）
trivy image --format sarif -o report.sarif nginx:latest

# 6. 忽略未修复的漏洞
trivy image --ignore-unfixed nginx:latest

# 7. 指定退出码（CI/CD 有用）
trivy image --exit-code 1 --severity CRITICAL nginx:latest
# 有 CRITICAL 漏洞时返回 1

# 8. 扫描 Dockerfile 配置问题
trivy config Dockerfile

# 9. 扫描 Kubernetes 配置
trivy config ./k8s/

# 10. 扫描文件系统漏洞
trivy fs --security-checks vuln,secret,config .
```

#### 3.2 Grype 安全扫描

```bash
# 1. 安装 Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# 2. 扫描镜像
grype nginx:latest

# 输出示例：
# NAME        INSTALLED   FIXED-IN  TYPE  VULNERABILITY   SEVERITY
# libssl3     3.0.11-1    3.0.13    deb   CVE-2024-0727   High

# 3. 只显示高危漏洞
grype nginx:latest --only-fixed --fail-on high

# 4. 输出 JSON 格式
grype nginx:latest -o json > report.json

# 5. 与 SBOM 配合使用
# 先生成 SBOM
syft nginx:latest -o spdx-json > sbom.json
# 使用 SBOM 扫描
grype sbom:sbom.json

# 6. 扫描目录
grype dir:./myapp

# 7. 指定数据库更新
grype db update

# 8. CI/CD 集成
grype nginx:latest --fail-on critical --only-fixed
# 有已修复的 CRITICAL 漏洞时返回非零
```

#### 3.3 Trivy vs Grype 对比

| 特性 | Trivy | Grype |
|------|-------|-------|
| 扫描类型 | 镜像/文件系统/Git/K8s | 镜像/目录/SBOM |
| 漏洞数据库 | NVD/GitHub Advisory/OS 等 | NVD/GitHub Advisory |
| 配置扫描 | 支持（misconfig） | 不支持 |
| 密钥扫描 | 支持（secret） | 不支持 |
| SBOM 生成 | 支持（内置） | 不支持（需 syft） |
| 速度 | 快 | 快 |
| CI/CD 集成 | GitHub Actions/GitLab CI 等 | GitHub Actions 等 |
| 输出格式 | JSON/SARIF/Table/CSV | JSON/Table/CycloneDX |
| 社区活跃度 | 非常高 | 高 |

**推荐选择：**
- 需要全面扫描（漏洞+配置+密钥）：Trivy
- 需要 SBOM 工作流：Grype + Syft
- CI/CD 集成：两者都很好，Trivy 略更成熟

#### 3.4 Docker Scout（Docker 官方方案）

```bash
# Docker Scout 是 Docker Desktop 内置的安全扫描工具

# 1. 启用 Docker Scout
docker scout quickview nginx:latest

# 2. 查看漏洞
docker scout cves nginx:latest

# 3. 查看推荐的基础镜像
docker scout recommendations nginx:latest

# 4. 比较两个镜像的安全状况
docker scout compare --to nginx:1.24 nginx:1.25

# 5. 输出 JSON
docker scout cves --format sarif nginx:latest

# 6. 在 CI/CD 中使用
# 需要登录 Docker Hub
docker login
docker scout cves --only-severity critical,high myimage:latest
```

---

### 4. CI/CD 安全扫描集成

#### 4.1 GitHub Actions 集成

```yaml
# .github/workflows/container-security.yml
name: Container Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: myapp:${{ github.sha }}

      # Trivy 扫描（漏洞）
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-vuln-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      # Trivy 扫描（配置）
      - name: Run Trivy config scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          format: 'table'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'

      # Trivy 扫描（密钥）
      - name: Run Trivy secret scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          security-checks: 'secret'
          format: 'table'
          exit-code: '1'

      # 上传扫描结果到 GitHub Security
      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-vuln-results.sarif'

      # Grype 扫描（补充）
      - name: Scan image with Grype
        uses: anchore/scan-action@v3
        with:
          image: myapp:${{ github.sha }}
          fail-build: true
          severity-cutoff: high
          output-format: sarif

      # 生成 SBOM
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: myapp:${{ github.sha }}
          format: spdx-json
          output-file: sbom.spdx.json

      # 上传 SBOM 作为 artifact
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json

      # 只有扫描通过才推送镜像
      - name: Login to Docker Hub
        if: github.ref == 'refs/heads/main'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_HUB_USERNAME }}
          password: ${{ secrets.DOCKER_HUB_TOKEN }}

      - name: Push image
        if: github.ref == 'refs/heads/main'
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            myapp:latest
            myapp:${{ github.sha }}
```

#### 4.2 GitLab CI 集成

```yaml
# .gitlab-ci.yml
stages:
  - build
  - scan
  - deploy

variables:
  IMAGE_NAME: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t $IMAGE_NAME .
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push $IMAGE_NAME

trivy-scan:
  stage: scan
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed $IMAGE_NAME
  allow_failure: false

grype-scan:
  stage: scan
  image:
    name: anchore/grype:latest
    entrypoint: [""]
  script:
    - grype $IMAGE_NAME --fail-on high --only-fixed
  allow_failure: false

docker-scout:
  stage: scan
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker scout cves --only-severity critical,high $IMAGE_NAME
  allow_failure: true

deploy:
  stage: deploy
  script:
    - echo "Deploying $IMAGE_NAME"
    # 部署逻辑
  only:
    - main
  when: on_success
```

#### 4.3 镜像签名与验证

```bash
# 使用 Cosign 进行镜像签名（Day 86 已详细讲解）

# CI/CD 中的签名流程
# 1. 构建镜像
docker build -t myregistry/myapp:v1 .

# 2. 推送镜像
docker push myregistry/myapp:v1

# 3. 签名镜像
cosign sign --key cosign.key myregistry/myapp:v1

# 4. 验证签名（部署前）
cosign verify --key cosign.pub myregistry/myapp:v1

# 5. 验证 SBOM
cosign verify-attestation --type spdxjson --key cosign.pub myregistry/myapp:v1
```

---

### 5. 生产环境检查清单

#### 5.1 Dockerfile 检查清单

```
┌─────────────────────────────────────────────────────────────┐
│                Dockerfile 生产检查清单                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   基础镜像                                                  │
│   ☐ 使用官方镜像或可信来源                                  │
│   ☐ 使用特定版本标签（非 latest）                           │
│   ☐ 使用最小基础镜像（alpine/distroless）                   │
│   ☐ 定期更新基础镜像                                        │
│                                                             │
│   构建优化                                                  │
│   ☐ 使用多阶段构建                                          │
│   ☐ 合理排序 COPY/ADD 指令（利用缓存）                      │
│   ☐ 使用 .dockerignore 排除不需要的文件                     │
│   ☐ 清理构建缓存和临时文件                                  │
│                                                             │
│   安全加固                                                  │
│   ☐ 创建并使用非 root 用户                                  │
│   ☐ 移除不必要的工具（curl/wget/git）                       │
│   ☐ 不要在镜像中硬编码密钥                                  │
│   ☐ 使用 COPY 而非 ADD（除非需要解压）                      │
│   ☐ 设置 HEALTHCHECK                                        │
│                                                             │
│   最佳实践                                                  │
│   ☐ 使用 dumb-init 或 tini 作为 PID 1                      │
│   ☐ 不要在构建时运行应用                                     │
│   ☐ 设置适当的文件权限                                       │
│   ☐ 使用 LABEL 添加元数据                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Docker Compose 检查清单

```
┌─────────────────────────────────────────────────────────────┐
│              Docker Compose 生产检查清单                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   资源管理                                                  │
│   ☐ 设置 memory 和 cpus 限制                                │
│   ☐ 设置 restart: unless-stopped                            │
│   ☐ 配置健康检查（healthcheck）                             │
│   ☐ 使用 depends_on + condition: service_healthy            │
│                                                             │
│   安全配置                                                  │
│   ☐ 使用 secrets 管理敏感信息                               │
│   ☐ 使用 internal 网络隔离后端服务                          │
│   ☐ 最小化端口暴露                                          │
│   ☐ 使用只读卷（:ro）挂载配置文件                           │
│                                                             │
│   日志与监控                                                │
│   ☐ 配置日志驱动和轮转                                      │
│   ☐ 设置适当的日志级别                                      │
│   ☐ 集成监控系统（Prometheus/cAdvisor）                     │
│                                                             │
│   持久化                                                    │
│   ☐ 使用命名卷存储数据                                      │
│   ☐ 定期备份数据卷                                          │
│   ☐ 不要在容器内存储持久化数据                              │
│                                                             │
│   网络                                                      │
│   ☐ 为不同服务创建独立网络                                  │
│   ☐ 限制容器间不必要的通信                                  │
│   ☐ 使用 DNS 名称而非 IP 地址                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.3 容器运行时检查清单

```
┌─────────────────────────────────────────────────────────────┐
│              容器运行时安全检查清单                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   权限控制                                                  │
│   ☐ 不使用 --privileged                                      │
│   ☐ 移除所有 capabilities（--cap-drop=ALL）                 │
│   ☐ 只添加必要的 capabilities                               │
│   ☐ 使用 --no-new-privileges                                │
│   ☐ 使用只读文件系统（--read-only）                         │
│                                                             │
│   安全模块                                                  │
│   ☐ 使用默认 seccomp profile                                │
│   ☐ 配置 AppArmor 或 SELinux                                │
│   ☐ 考虑 user namespace 重映射                              │
│                                                             │
│   资源限制                                                  │
│   ☐ 设置内存限制（--memory）                                │
│   ☐ 设置 CPU 限制（--cpus）                                 │
│   ☐ 设置 PID 限制（--pids-limit）                           │
│   ☐ 设置重启策略（--restart）                               │
│                                                             │
│   网络安全                                                  │
│   ☐ 限制端口绑定（-p 127.0.0.1:port:port）                 │
│   ☐ 使用自定义网络                                          │
│   ☐ 禁用不必要的网络功能                                    │
│                                                             │
│   镜像安全                                                  │
│   ☐ 定期扫描镜像漏洞                                        │
│   ☐ 使用镜像签名（Content Trust）                           │
│   ☐ 只从可信仓库拉取镜像                                    │
│   ☐ 使用镜像摘要而非标签                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.4 部署前完整检查脚本

```bash
#!/bin/bash
# pre-deploy-check.sh - 部署前安全检查

set -e

echo "==================== 部署前检查 ===================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

ERRORS=0
WARNINGS=0

# 1. 检查 Dockerfile
echo ""
echo "--- Dockerfile 检查 ---"

if grep -q "FROM.*:latest" Dockerfile; then
    fail "使用了 latest 标签"
    ERRORS=$((ERRORS + 1))
else
    pass "使用了特定版本标签"
fi

if grep -q "^USER" Dockerfile; then
    pass "设置了非 root 用户"
else
    fail "未设置 USER 指令"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "HEALTHCHECK" Dockerfile; then
    pass "设置了健康检查"
else
    warn "未设置 HEALTHCHECK"
    WARNINGS=$((WARNINGS + 1))
fi

if grep -q "FROM.*as.*builder" Dockerfile || grep -q "FROM.*AS.*builder" Dockerfile; then
    pass "使用了多阶段构建"
else
    warn "未使用多阶段构建"
    WARNINGS=$((WARNINGS + 1))
fi

# 2. 安全扫描
echo ""
echo "--- 安全扫描 ---"

if command -v trivy &> /dev/null; then
    IMAGE_NAME=$1
    if [ -n "$IMAGE_NAME" ]; then
        echo "扫描镜像: $IMAGE_NAME"
        CRITICAL=$(trivy image --severity CRITICAL --format json "$IMAGE_NAME" 2>/dev/null | jq '.Results[].Vulnerabilities | length' | awk '{s+=$1} END {print s}')
        if [ "$CRITICAL" -gt 0 ]; then
            fail "发现 $CRITICAL 个 CRITICAL 漏洞"
            ERRORS=$((ERRORS + 1))
        else
            pass "无 CRITICAL 漏洞"
        fi
    fi
else
    warn "Trivy 未安装，跳过漏洞扫描"
fi

# 3. Docker Compose 检查
echo ""
echo "--- Docker Compose 检查 ---"

if [ -f "docker-compose.yml" ]; then
    # 检查是否设置了资源限制
    if grep -q "limits:" docker-compose.yml; then
        pass "设置了资源限制"
    else
        warn "未设置资源限制"
        WARNINGS=$((WARNINGS + 1))
    fi

    # 检查是否使用了 secrets
    if grep -q "secrets:" docker-compose.yml; then
        pass "使用了 secrets"
    else
        warn "未使用 secrets（检查是否有硬编码密码）"
        WARNINGS=$((WARNINGS + 1))
    fi

    # 检查是否使用了 internal 网络
    if grep -q "internal: true" docker-compose.yml; then
        pass "使用了内部网络隔离"
    else
        warn "未使用 internal 网络"
        WARNINGS=$((WARNINGS + 1))
    fi

    # 检查是否有健康检查
    healthcheck_count=$(grep -c "healthcheck:" docker-compose.yml || true)
    service_count=$(grep -c "image:" docker-compose.yml || true)
    if [ "$healthcheck_count" -eq "$service_count" ]; then
        pass "所有服务都设置了健康检查"
    else
        warn "部分服务未设置健康检查 ($healthcheck_count/$service_count)"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 4. 密钥检查
echo ""
echo "--- 密钥检查 ---"

# 检查是否有硬编码的密码
if grep -rn "password\|secret\|token\|api_key" --include="*.yml" --include="*.yaml" . 2>/dev/null | grep -v "secrets\|FILE\|_PW\|_KEY:" | grep -q "="; then
    warn "可能存在硬编码密码"
    WARNINGS=$((WARNINGS + 1))
else
    pass "未发现硬编码密码"
fi

# 检查 .env 文件
if [ -f ".env" ]; then
    warn ".env 文件存在，确保已添加到 .gitignore"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. 汇总
echo ""
echo "==================== 检查结果 ===================="
echo -e "错误: ${RED}$ERRORS${NC}"
echo -e "警告: ${YELLOW}$WARNINGS${NC}"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}部署前检查失败！请修复错误后重试。${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}检查通过，但有警告需要关注。${NC}"
    exit 0
else
    echo -e "${GREEN}所有检查通过！${NC}"
    exit 0
fi
```

---

## 💻 实战练习

### 练习 1：部署完整的 LNMP 应用

**目标：** 使用 Docker Compose 部署一个 WordPress 站点。

```bash
# 1. 创建项目目录
mkdir -p wordpress/{nginx,php,mysql,secrets}
cd wordpress

# 2. 创建密钥文件
echo "StrongRootPassword123!" > secrets/mysql_root_password.txt
echo "StrongAppPassword456!" > secrets/mysql_password.txt
chmod 600 secrets/*.txt

# 3. 创建 Nginx 配置
cat > nginx/default.conf << 'EOF'
server {
    listen 80;
    server_name localhost;
    root /var/www/html;
    index index.php index.html;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        fastcgi_pass php:9000;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# 4. 创建 docker-compose.yml
cat > docker-compose.yml << 'COMPOSE'
version: '3.8'

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - wp-data:/var/www/html
    depends_on:
      - php
    networks:
      - frontend

  php:
    image: wordpress:6.4-php8.2-fpm-alpine
    volumes:
      - wp-data:/var/www/html
    environment:
      WORDPRESS_DB_HOST: mysql:3306
      WORDPRESS_DB_NAME: wordpress
      WORDPRESS_DB_USER: wpuser
      WORDPRESS_DB_PASSWORD_FILE: /run/secrets/mysql_password
    secrets:
      - mysql_password
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - frontend
      - backend

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wpuser
      MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
    secrets:
      - mysql_root_password
      - mysql_password
    volumes:
      - mysql-data:/var/lib/mysql
    networks:
      - backend
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  wp-data:
  mysql-data:

networks:
  frontend:
  backend:
    internal: true

secrets:
  mysql_root_password:
    file: ./secrets/mysql_root_password.txt
  mysql_password:
    file: ./secrets/mysql_password.txt
COMPOSE

# 5. 启动服务
docker compose up -d

# 6. 验证
docker compose ps
curl -I http://localhost:8080

# 7. 完成 WordPress 安装
# 浏览器访问 http://localhost:8080
```

### 练习 2：容器安全扫描实战

**目标：** 使用 Trivy 和 Grype 扫描镜像并修复漏洞。

```bash
# 1. 构建一个有漏洞的镜像
cat > Dockerfile << 'EOF'
FROM node:14
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
EOF

# 创建简单的应用
cat > package.json << 'EOF'
{
  "name": "vuln-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "4.17.1",
    "lodash": "4.17.19"
  }
}
EOF

cat > server.js << 'EOF'
const express = require('express');
const app = express();
app.get('/', (req, res) => res.send('Hello World'));
app.listen(3000);
EOF

# 2. 构建镜像
docker build -t vuln-app:v1 .

# 3. 使用 Trivy 扫描
echo "=== Trivy 扫描结果 ==="
trivy image vuln-app:v1

echo ""
echo "=== 只显示高危漏洞 ==="
trivy image --severity HIGH,CRITICAL vuln-app:v1

# 4. 使用 Grype 扫描
echo ""
echo "=== Grype 扫描结果 ==="
grype vuln-app:v1

# 5. 修复：更新基础镜像和依赖
cat > Dockerfile.fixed << 'EOF'
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser
USER appuser
EXPOSE 3000
CMD ["node", "server.js"]
EOF

# 更新 package.json
cat > package.json << 'EOF'
{
  "name": "fixed-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "^4.17.21"
  }
}
EOF

# 6. 重新构建和扫描
docker build -f Dockerfile.fixed -t vuln-app:v2 .
trivy image --severity HIGH,CRITICAL vuln-app:v2

# 7. 生成 SBOM
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/syft packages vuln-app:v2 -o spdx-json > sbom.json

# 8. 使用 SBOM 扫描
grype sbom:sbom.json
```

### 练习 3：生产部署检查

**目标：** 对部署配置进行全面的安全和质量检查。

```bash
# 1. 创建生产级 docker-compose
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  web:
    image: myapp:v1
    ports:
      - "80:3000"
    environment:
      - NODE_ENV=production
      - DB_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - db-data:/var/lib/postgresql/data
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  db-data:

networks:
  backend:
    internal: true

secrets:
  db_password:
    file: ./secrets/db_password.txt
EOF

# 2. 运行检查脚本
chmod +x pre-deploy-check.sh
./pre-deploy-check.sh myapp:v1

# 3. 手动检查项
echo "=== 手动检查 ==="

# 检查端口暴露
docker compose -f docker-compose.prod.yml config | grep -A2 "ports:"

# 检查卷挂载
docker compose -f docker-compose.prod.yml config | grep -A2 "volumes:"

# 检查网络配置
docker compose -f docker-compose.prod.yml config | grep -A2 "networks:"

# 4. 安全扫描
trivy image myapp:v1

# 5. Docker Bench Security
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  docker/docker-bench-security

# 6. 启动并验证
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs
```

---

## 🎯 面试题精选

### 1. 如何设计一个生产级的 Docker Compose 应用？

**参考答案：**

生产级 Docker Compose 需要包含：

1. **安全配置**：使用 secrets 管理密码、internal 网络隔离、非 root 用户
2. **资源限制**：每个服务设置 memory 和 cpus 限制
3. **健康检查**：所有服务配置 healthcheck，使用 depends_on condition
4. **日志管理**：配置日志驱动和轮转
5. **持久化**：使用命名卷存储数据
6. **重启策略**：restart: unless-stopped
7. **最小化端口暴露**：只暴露必需端口

### 2. Trivy 和 Grype 有什么区别？如何选择？

**参考答案：**

| 特性 | Trivy | Grype |
|------|-------|-------|
| 扫描类型 | 漏洞+配置+密钥+K8s | 漏洞+SBOM |
| SBOM 生成 | 内置 | 需 syft |
| 配置扫描 | 支持 | 不支持 |
| 密钥扫描 | 支持 | 不支持 |
| CI/CD 集成 | 非常成熟 | 成熟 |

选择建议：需要全面扫描用 Trivy，SBOM 工作流用 Grype+Syft。生产环境建议两者结合使用。

### 3. 如何在 CI/CD 中集成容器安全扫描？

**参考答案：**

```yaml
# GitHub Actions 示例
jobs:
  security:
    steps:
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: 1

      - name: Push if safe
        if: success()
        run: docker push myapp:${{ github.sha }}
```

关键点：
- 扫描失败时阻止推送（exit-code: 1）
- 上传 SARIF 到 GitHub Security tab
- 生成 SBOM 作为附件
- 使用镜像摘要（digest）确保可追溯

### 4. 容器安全扫描应该扫描哪些内容？

**参考答案：**

容器安全扫描应覆盖四个维度：

1. **漏洞扫描**：OS 包和应用依赖的已知漏洞
2. **配置扫描**：Dockerfile 和 K8s 配置的最佳实践违规
3. **密钥扫描**：代码和镜像中的硬编码密码、API Key
4. **SBOM 生成**：软件物料清单，追踪所有组件

```bash
trivy image myapp:v1         # 漏洞
trivy config .               # 配置
trivy fs --scanners secret . # 密钥
```

### 5. 微服务架构中如何管理容器间的通信？

**参考答案：**

1. **服务发现**：Docker Compose 使用服务名，K8s 使用 Service
2. **网络隔离**：使用 internal 网络，frontend/backend 分离
3. **通信方式**：
   - 同步：HTTP/gRPC（简单直接）
   - 异步：消息队列（解耦、削峰）
4. **API Gateway**：统一入口，路由、限流、认证
5. **安全**：mTLS 加密、网络策略限制

### 6. 如何实现容器的零停机部署？

**参考答案：**

```bash
# 1. 使用 Docker Compose 的 rolling update
deploy:
  replicas: 3
  update_config:
    parallelism: 1
    delay: 30s
    order: start-first  # 先启动新容器再停止旧容器

# 2. 健康检查确保新容器就绪
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 30s

# 3. Nginx/Traefik 自动发现新容器
# 4. 旧容器优雅关闭
stop_grace_period: 30s
```

### 7. 如何管理 Docker 容器中的敏感信息？

**参考答案：**

**不推荐的做法：**
- 环境变量中的密码：`docker run -e DB_PASSWORD=secret`
- Dockerfile 中的密钥：`ENV API_KEY=xxx`
- 代码中的硬编码密码

**推荐的做法：**

```yaml
# 1. Docker Secrets（Swarm 模式）
secrets:
  db_password:
    file: ./secrets/db_password.txt
services:
  app:
    secrets:
      - db_password

# 2. Docker Compose secrets
secrets:
  db_password:
    file: ./secrets/db_password.txt

# 3. 外部密钥管理
# - HashiCorp Vault
# - AWS Secrets Manager
# - Azure Key Vault
```

### 8. 如何优化 Docker 镜像大小？

**参考答案：**

```dockerfile
# 1. 使用小基础镜像
FROM node:20-alpine  # ~50MB vs node:20 ~350MB

# 2. 多阶段构建
FROM node:20-alpine AS builder
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# 3. 合并 RUN 指令
RUN apk add --no-cache curl git && \
    npm install && \
    npm cache clean --force && \
    apk del curl git

# 4. 使用 .dockerignore
# node_modules
# .git
# *.md
# .env
```

### 9. 容器日志的最佳实践是什么？

**参考答案：**

1. **应用层面**：
   - 输出到 stdout/stderr（而非文件）
   - 使用结构化日志（JSON 格式）
   - 设置适当的日志级别

2. **Docker 层面**：
   - 配置日志轮转（max-size, max-file）
   - 选择合适的日志驱动
   - 生产环境使用集中日志系统

3. **运维层面**：
   - 监控日志磁盘使用
   - 设置日志告警
   - 定期归档历史日志

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5",
    "compress": "true"
  }
}
```

### 10. 如何进行容器的容量规划？

**参考答案：**

容器容量规划需要考虑：

1. **资源评估**：
   - CPU：通过压测确定每个服务的 CPU 需求
   - 内存：观察生产环境的内存使用峰值
   - 磁盘：预估数据增长速度
   - 网络：评估带宽需求

2. **冗余设计**：
   - 服务副本数 >= 2（高可用）
   - 数据库主从复制
   - 跨可用区部署

3. **弹性策略**：
   - 设置资源 limits 和 requests
   - 配置自动扩缩容（HPA）
   - 预留 20-30% 的资源缓冲

4. **监控指标**：
   - CPU/内存使用率趋势
   - 请求量和响应时间
   - 错误率和成功率

---

## 📚 深入阅读

### 官方文档
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Grype Documentation](https://github.com/anchore/grype)
- [Docker Bench Security](https://github.com/docker/docker-bench-security)

### 最佳实践
- [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [12 Factor App](https://12factor.net/)

---

## ✅ 自检清单

### 多容器部署
- [ ] 能够使用 Docker Compose 部署 LAMP/LNMP 应用
- [ ] 理解微服务架构的容器化模式
- [ ] 掌握服务间通信和网络隔离
- [ ] 能够配置健康检查和资源限制

### 安全扫描
- [ ] 掌握 Trivy 镜像漏洞扫描
- [ ] 掌握 Grype 安全扫描
- [ ] 理解 SBOM 生成和使用
- [ ] 能够在 CI/CD 中集成安全扫描

### 生产部署
- [ ] 掌握 Dockerfile 生产检查清单
- [ ] 掌握 Docker Compose 生产配置
- [ ] 理解容器运行时安全加固
- [ ] 能够进行部署前安全检查

### 综合能力
- [ ] 能够设计完整的容器化应用架构
- [ ] 能够实施容器安全最佳实践
- [ ] 能够排查容器化应用的常见问题
- [ ] 准备好进入 Kubernetes 学习阶段

---

## 🔧 常见问题与故障排查

### 问题 1：Docker Compose 服务启动顺序问题

```bash
# 问题：应用连接数据库失败
# 原因：数据库未完全启动时应用就开始连接

# 解决方案：使用 depends_on + healthcheck
services:
  app:
    depends_on:
      db:
        condition: service_healthy

  db:
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

# 应用层面也要实现重试逻辑
```

### 问题 2：容器间 DNS 解析失败

```bash
# 检查网络
docker network ls
docker network inspect <network_name>

# 检查容器是否在同一网络
docker inspect --format='{{json .NetworkSettings.Networks}}' container1
docker inspect --format='{{json .NetworkSettings.Networks}}' container2

# 测试 DNS
docker exec container1 nslookup container2
```

### 问题 3：安全扫描误报处理

```bash
# Trivy 忽略特定漏洞
cat > .trivyignore << 'EOF'
# CVE-2023-XXXX - Not applicable to our usage
CVE-2023-XXXX
EOF

trivy image --ignorefile .trivyignore myapp:v1

# Grype 忽略特定漏洞
cat > .grype.yaml << 'EOF'
ignore:
  - vulnerability: CVE-2023-XXXX
    reason: Not applicable
EOF

grype --config .grype.yaml myapp:v1
```

---

**恭喜完成 Docker 阶段学习！** 接下来将进入 Kubernetes 学习阶段，Day 90 开始将学习 Kubernetes 基础概念和架构。
