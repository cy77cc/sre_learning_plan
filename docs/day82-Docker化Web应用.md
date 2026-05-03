# Day 82: Docker 化 Web 应用

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 化 Web 应用
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 77 (Docker 镜像基础), Day 78 (Dockerfile 进阶构建), Day 80 (Docker 数据管理), Day 81 (Docker 网络管理)

## 🎯 学习目标

- 掌握 Nginx + PHP-FPM 的 Docker 化部署与反向代理配置
- 掌握 Node.js 应用的多阶段构建与生产部署
- 掌握 Python Flask 应用的 Docker 化最佳实践
- 掌握 Go 微服务的最小化容器构建
- 理解环境变量与配置管理在容器化场景中的设计
- 能编排完整的多服务应用（Web + API + DB + Cache）

---

## 📖 核心知识点

### 1. Nginx + PHP-FPM 容器化

#### 1.1 架构设计

```
Nginx + PHP-FPM 多容器架构:

┌────────────────────────────────────────────────────┐
│                  Docker Host                        │
│                                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │              frontend-net                    │  │
│  │                                              │  │
│  │  ┌──────────────┐     ┌──────────────────┐  │  │
│  │  │    nginx      │     │   php-fpm        │  │  │
│  │  │  :80/:443     │────▶│  :9000           │  │  │
│  │  │  (反向代理)    │     │  (PHP 解析)       │  │  │
│  │  └──────┬───────┘     └────────┬─────────┘  │  │
│  └─────────┼──────────────────────┼────────────┘  │
│            │                      │               │
│  ┌─────────┼──────────────────────┼────────────┐  │
│  │         │    backend-net       │            │  │
│  │         │                      │            │  │
│  │         │     ┌────────────────┴─────────┐  │  │
│  │         │     │         mysql            │  │  │
│  │         │     │        :3306             │  │  │
│  │         │     └──────────────────────────┘  │  │
│  │         │                                   │  │
│  │         │     ┌──────────────────────────┐  │  │
│  │         │     │         redis            │  │  │
│  │         └────▶│        :6379             │  │  │
│  │               └──────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘

请求流程:
Client → Nginx (:80) → PHP-FPM (:9000) → MySQL/Redis
         静态文件直接返回    FastCGI 协议
```

#### 1.2 项目结构

```
nginx-php-app/
├── docker-compose.yml
├── nginx/
│   ├── Dockerfile
│   └── conf.d/
│       └── default.conf
├── php/
│   ├── Dockerfile
│   └── php.ini
├── src/
│   ├── index.php
│   ├── api/
│   │   └── health.php
│   └── config/
│       └── database.php
└── .env
```

#### 1.3 PHP-FPM Dockerfile

```dockerfile
# php/Dockerfile
FROM php:8.2-fpm-bookworm

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpng-dev \
    libjpeg62-turbo-dev \
    libfreetype6-dev \
    libzip-dev \
    libicu-dev \
    libonig-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 PHP 扩展
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
    gd \
    pdo \
    pdo_mysql \
    mysqli \
    zip \
    intl \
    opcache \
    mbstring \
    bcmath

# 安装 Redis 扩展
RUN pecl install redis && docker-php-ext-enable redis

# 配置 PHP
COPY php.ini /usr/local/etc/php/conf.d/custom.ini

# 创建非 root 用户
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/false -d /app appuser

# 设置工作目录和权限
WORKDIR /app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 9000
CMD ["php-fpm"]
```

#### 1.4 PHP 配置文件

```ini
; php/php.ini
[PHP]
; 生产环境配置
display_errors = Off
error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT
log_errors = On
error_log = /proc/self/fd/2

; 性能优化
opcache.enable = 1
opcache.memory_consumption = 128
opcache.interned_strings_buffer = 8
opcache.max_accelerated_files = 10000
opcache.revalidate_freq = 0
opcache.validate_timestamps = 0
opcache.save_comments = 1

; 内存和执行时间
memory_limit = 256M
max_execution_time = 30
max_input_time = 60

; 文件上传
upload_max_filesize = 64M
post_max_size = 64M

; 时区
date.timezone = Asia/Shanghai

; Session
session.save_handler = redis
session.save_path = "tcp://redis:6379?auth=${REDIS_PASSWORD}"

[FPM]
; 通过环境变量动态配置
; docker run -e FPM_PM=dynamic -e FPM_MAX_CHILDREN=50
```

#### 1.5 Nginx 配置

```nginx
# nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;
    root /var/www/html/public;
    index index.php index.html;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 日志格式
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff2|woff|ttf|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # PHP 处理
    location ~ \.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass php:9000;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_param HTTPS off;

        # 超时配置
        fastcgi_connect_timeout 60s;
        fastcgi_send_timeout 300s;
        fastcgi_read_timeout 300s;

        # 缓冲配置
        fastcgi_buffer_size 32k;
        fastcgi_buffers 16 16k;
        fastcgi_busy_buffers_size 64k;
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # 拒绝访问隐藏文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # 根路由
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
}
```

#### 1.6 PHP 应用代码

```php
<?php
// src/index.php
declare(strict_types=1);

require_once __DIR__ . '/config/database.php';

$requestUri = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];

header('Content-Type: application/json; charset=utf-8');

try {
    $pdo = getDatabaseConnection();
    $redis = getRedisConnection();

    // 简单路由
    switch (true) {
        case $requestUri === '/api/health':
            $dbOk = false;
            $redisOk = false;

            try {
                $pdo->query('SELECT 1');
                $dbOk = true;
            } catch (Exception $e) {
                $dbOk = false;
            }

            try {
                $redis->ping();
                $redisOk = true;
            } catch (Exception $e) {
                $redisOk = false;
            }

            http_response_code($dbOk && $redisOk ? 200 : 503);
            echo json_encode([
                'status' => $dbOk && $redisOk ? 'healthy' : 'degraded',
                'timestamp' => date('c'),
                'checks' => [
                    'database' => $dbOk ? 'ok' : 'fail',
                    'redis' => $redisOk ? 'ok' : 'fail',
                ],
                'version' => getenv('APP_VERSION') ?: '1.0.0',
            ]);
            break;

        case $requestUri === '/api/info':
            echo json_encode([
                'app' => getenv('APP_NAME') ?: 'PHP App',
                'version' => getenv('APP_VERSION') ?: '1.0.0',
                'environment' => getenv('APP_ENV') ?: 'production',
                'php_version' => PHP_VERSION,
                'server_time' => date('c'),
            ]);
            break;

        default:
            // 访问计数
            $count = $redis->incr('page_views');
            echo json_encode([
                'message' => 'Welcome to Docker PHP App',
                'page_views' => $count,
                'host' => gethostname(),
            ]);
    }
} catch (Exception $e) {
    http_response_code(500);
    error_log("Application error: " . $e->getMessage());
    echo json_encode([
        'error' => 'Internal Server Error',
        'message' => getenv('APP_DEBUG') === 'true' ? $e->getMessage() : 'Something went wrong',
    ]);
}
```

```php
<?php
// src/config/database.php
declare(strict_types=1);

function getDatabaseConnection(): PDO
{
    static $pdo = null;

    if ($pdo === null) {
        $host = getenv('DB_HOST') ?: 'mysql';
        $port = getenv('DB_PORT') ?: '3306';
        $dbname = getenv('DB_NAME') ?: 'app';
        $username = getenv('DB_USER') ?: 'app';
        $password = getenv('DB_PASSWORD') ?: '';

        $dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset=utf8mb4";

        $pdo = new PDO($dsn, $username, $password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
            PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4",
        ]);
    }

    return $pdo;
}

function getRedisConnection(): Redis
{
    static $redis = null;

    if ($redis === null) {
        $host = getenv('REDIS_HOST') ?: 'redis';
        $port = (int)(getenv('REDIS_PORT') ?: 6379);
        $password = getenv('REDIS_PASSWORD') ?: null;
        $database = (int)(getenv('REDIS_DB') ?: 0);

        $redis = new Redis();
        $redis->connect($host, $port, 5.0);

        if ($password) {
            $redis->auth($password);
        }

        $redis->select($database);
    }

    return $redis;
}
```

#### 1.7 Nginx Dockerfile

```dockerfile
# nginx/Dockerfile
FROM nginx:1.25-alpine

# 删除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制自定义配置
COPY conf.d/ /etc/nginx/conf.d/

# 创建缓存目录并设置权限
RUN mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

EXPOSE 80 443
```

#### 1.8 Docker Compose 编排

```yaml
# docker-compose.yml
services:
  nginx:
    build:
      context: ./nginx
      dockerfile: Dockerfile
    ports:
      - "${HTTP_PORT:-80}:80"
    volumes:
      - ./src:/var/www/html:ro
    depends_on:
      php:
        condition: service_healthy
    networks:
      - frontend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M

  php:
    build:
      context: ./php
      dockerfile: Dockerfile
    volumes:
      - ./src:/app
    environment:
      - APP_ENV=${APP_ENV:-production}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_NAME=${APP_NAME:-PHP App}
      - APP_VERSION=${APP_VERSION:-1.0.0}
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-app}
      - DB_USER=${DB_USER:-app}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - frontend
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "php-fpm-healthcheck || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-app}
      MYSQL_USER: ${DB_USER:-app}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  mysql_data:
  redis_data:
```

---

### 2. Node.js 应用 Docker 化

#### 2.1 项目结构

```
node-app/
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── package.json
├── package-lock.json
├── src/
│   ├── index.js
│   ├── routes/
│   │   ├── health.js
│   │   └── api.js
│   ├── middleware/
│   │   └── logger.js
│   └── config/
│       └── index.js
└── .env
```

#### 2.2 Node.js Dockerfile（多阶段构建）

```dockerfile
# --- Stage 1: 依赖安装 ---
FROM node:20-alpine AS deps
WORKDIR /app

# 只复制 package 文件（利用缓存）
COPY package.json package-lock.json ./

# 使用 ci 安装精确版本的依赖
RUN npm ci --only=production && \
    # 分离开发依赖，后续只需要生产依赖
    cp -R node_modules /prod_node_modules && \
    npm ci

# --- Stage 2: 构建（如果有 TypeScript 等）---
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 运行构建（TypeScript 编译、前端打包等）
# RUN npm run build
# 如果是纯 JS 项目，此阶段可简化

# --- Stage 3: 生产镜像 ---
FROM node:20-alpine AS production

# 安全加固: 只安装必要的运行时
RUN apk --no-cache add \
    dumb-init \
    curl \
    && rm -rf /var/cache/apk/*

# 设置时区
RUN apk --no-cache add tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apk del tzdata

# 创建非 root 用户
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

WORKDIR /app

# 复制生产依赖
COPY --from=deps /prod_node_modules ./node_modules

# 复制应用代码
COPY --chown=appuser:appgroup package.json ./
COPY --chown=appuser:appgroup src/ ./src/

# 设置环境变量
ENV NODE_ENV=production \
    PORT=3000

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# 使用 dumb-init 作为 PID 1 进程，正确处理信号
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "src/index.js"]
```

#### 2.3 Node.js 应用代码

```javascript
// src/index.js
const http = require('http');
const { URL } = require('url');

const PORT = process.env.PORT || 3000;
const HOSTNAME = process.env.HOSTNAME || '0.0.0.0';

// 路由处理
const routes = {
  'GET /health': (req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      version: process.env.APP_VERSION || '1.0.0',
    }));
  },

  'GET /api/info': (req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      app: process.env.APP_NAME || 'Node.js App',
      version: process.env.APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      node_version: process.version,
      host: require('os').hostname(),
    }));
  },

  'GET /': (req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      message: 'Welcome to Docker Node.js App',
      endpoints: ['/health', '/api/info'],
    }));
  },
};

const server = http.createServer((req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const routeKey = `${req.method} ${parsedUrl.pathname}`;

  if (routes[routeKey]) {
    routes[routeKey](req, res);
  } else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not Found' }));
  }
});

// 优雅关闭
const gracefulShutdown = (signal) => {
  console.log(`Received ${signal}. Starting graceful shutdown...`);
  server.close(() => {
    console.log('Server closed. Exiting.');
    process.exit(0);
  });

  // 超时强制退出
  setTimeout(() => {
    console.error('Graceful shutdown timeout. Forcefully exiting.');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

server.listen(PORT, HOSTNAME, () => {
  console.log(`Server running at http://${HOSTNAME}:${PORT}/`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});
```

#### 2.4 Node.js 环境变量与配置管理

```javascript
// src/config/index.js
const config = {
  port: parseInt(process.env.PORT, 10) || 3000,
  host: process.env.HOST || '0.0.0.0',
  nodeEnv: process.env.NODE_ENV || 'development',

  // 数据库配置
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT, 10) || 5432,
    name: process.env.DB_NAME || 'app',
    user: process.env.DB_USER || 'app',
    password: process.env.DB_PASSWORD || '',
    poolSize: parseInt(process.env.DB_POOL_SIZE, 10) || 10,
  },

  // Redis 配置
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT, 10) || 6379,
    password: process.env.REDIS_PASSWORD || '',
    db: parseInt(process.env.REDIS_DB, 10) || 0,
  },

  // 日志配置
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    format: process.env.LOG_FORMAT || 'json',
  },
};

// 验证必需的配置
const requiredEnvVars = ['DB_PASSWORD'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`Missing required environment variable: ${envVar}`);
    process.exit(1);
  }
}

module.exports = config;
```

---

### 3. Python Flask 应用 Docker 化

#### 3.1 Flask Dockerfile

```dockerfile
# --- Stage 1: 构建阶段 ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: 生产镜像 ---
FROM python:3.12-slim-bookworm AS production

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/false -m appuser

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# 复制应用代码
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 使用 gunicorn 作为生产 WSGI 服务器
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "app:create_app()"]
```

#### 3.2 Flask 应用代码

```python
# app.py
import os
import time
import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request
import redis
import pymysql

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # 配置
    app.config.update(
        APP_NAME=os.getenv('APP_NAME', 'Flask App'),
        APP_VERSION=os.getenv('APP_VERSION', '1.0.0'),
        APP_ENV=os.getenv('APP_ENV', 'production'),
        DB_HOST=os.getenv('DB_HOST', 'mysql'),
        DB_PORT=int(os.getenv('DB_PORT', 3306)),
        DB_NAME=os.getenv('DB_NAME', 'app'),
        DB_USER=os.getenv('DB_USER', 'app'),
        DB_PASSWORD=os.getenv('DB_PASSWORD', ''),
        REDIS_HOST=os.getenv('REDIS_HOST', 'redis'),
        REDIS_PORT=int(os.getenv('REDIS_PORT', 6379)),
        REDIS_PASSWORD=os.getenv('REDIS_PASSWORD', ''),
    )

    # 初始化 Redis 连接
    redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        password=app.config['REDIS_PASSWORD'] or None,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )

    def get_db():
        return pymysql.connect(
            host=app.config['DB_HOST'],
            port=app.config['DB_PORT'],
            database=app.config['DB_NAME'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )

    @app.before_request
    def before_request():
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        duration = time.time() - getattr(request, 'start_time', time.time())
        logger.info(
            f"{request.method} {request.path} "
            f"status={response.status_code} "
            f"duration={duration:.4f}s "
            f"ip={request.remote_addr}"
        )
        return response

    @app.route('/health')
    def health():
        checks = {}
        healthy = True

        # 检查数据库
        try:
            conn = get_db()
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
            conn.close()
            checks['database'] = 'ok'
        except Exception as e:
            checks['database'] = f'fail: {str(e)}'
            healthy = False

        # 检查 Redis
        try:
            redis_client.ping()
            checks['redis'] = 'ok'
        except Exception as e:
            checks['redis'] = f'fail: {str(e)}'
            healthy = False

        status_code = 200 if healthy else 503
        return jsonify({
            'status': 'healthy' if healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': checks,
            'version': app.config['APP_VERSION'],
            'hostname': os.uname().nodename,
        }), status_code

    @app.route('/api/info')
    def info():
        return jsonify({
            'app': app.config['APP_NAME'],
            'version': app.config['APP_VERSION'],
            'environment': app.config['APP_ENV'],
            'python_version': os.sys.version,
            'hostname': os.uname().nodename,
        })

    @app.route('/')
    def index():
        count = redis_client.incr('page_views')
        return jsonify({
            'message': 'Welcome to Docker Flask App',
            'page_views': count,
            'hostname': os.uname().nodename,
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not Found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal error: {str(e)}")
        return jsonify({'error': 'Internal Server Error'}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
```

```txt
# requirements.txt
flask==3.0.0
gunicorn==21.2.0
redis==5.0.1
pymysql==1.1.0
cryptography==41.0.7
```

---

### 4. Go 微服务 Docker 化

#### 4.1 Go 微服务 Dockerfile

```dockerfile
# --- Stage 1: 构建 ---
FROM golang:1.22-alpine AS builder

# 安装构建依赖
RUN apk --no-cache add \
    git \
    ca-certificates \
    tzdata

WORKDIR /app

# 先复制依赖文件（利用缓存）
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# 复制源代码
COPY . .

# 编译 - 静态链接，最小化二进制
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -ldflags="-w -s -X main.version=$(git describe --tags --always 2>/dev/null || echo 'dev') \
              -X main.buildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    -trimpath \
    -o /app/server \
    ./cmd/server

# --- Stage 2: 生产镜像 (scratch 或 distroless) ---
FROM scratch AS production

# 从 builder 复制必要的文件
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/server /server

# 配置
ENV TZ=Asia/Shanghai \
    GIN_MODE=release

EXPOSE 8080

ENTRYPOINT ["/server"]
```

如果需要更多调试能力，可以使用 `alpine` 替代 `scratch`:

```dockerfile
FROM alpine:3.19 AS production

RUN apk --no-cache add \
    ca-certificates \
    tzdata \
    && addgroup -g 1000 appgroup \
    && adduser -u 1000 -G appgroup -s /bin/sh -D appuser

WORKDIR /app
COPY --from=builder /app/server .

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost:8080/health || exit 1

ENTRYPOINT ["./server"]
```

#### 4.2 Go 微服务代码

```go
// cmd/server/main.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"
)

var (
	version    = "dev"
	buildTime  = "unknown"
)

type HealthResponse struct {
	Status    string            `json:"status"`
	Timestamp string            `json:"timestamp"`
	Version   string            `json:"version"`
	Checks    map[string]string `json:"checks"`
	Uptime    string            `json:"uptime"`
}

type InfoResponse struct {
	App         string `json:"app"`
	Version     string `json:"version"`
	BuildTime   string `json:"build_time"`
	GoVersion   string `json:"go_version"`
	Environment string `json:"environment"`
	Hostname    string `json:"hostname"`
}

var startTime = time.Now()

func healthHandler(w http.ResponseWriter, r *http.Request) {
	resp := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Version:   version,
		Checks: map[string]string{
			"server": "ok",
		},
		Uptime: time.Since(startTime).Round(time.Second).String(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func infoHandler(w http.ResponseWriter, r *http.Request) {
	hostname, _ := os.Hostname()

	resp := InfoResponse{
		App:         getEnv("APP_NAME", "Go Microservice"),
		Version:     version,
		BuildTime:   buildTime,
		GoVersion:   runtime.Version(),
		Environment: getEnv("APP_ENV", "production"),
		Hostname:    hostname,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

func main() {
	port := getEnv("PORT", "8080")

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/api/info", infoHandler)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"message":    "Welcome to Go Microservice",
			"version":    version,
			"build_time": buildTime,
		})
	})

	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", port),
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// 优雅关闭
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigChan
		log.Printf("Received signal %v. Starting graceful shutdown...", sig)

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		if err := server.Shutdown(ctx); err != nil {
			log.Printf("Server shutdown error: %v", err)
		}
		log.Println("Server stopped.")
	}()

	log.Printf("Starting server on :%s (version: %s, built: %s)", port, version, buildTime)
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("Server error: %v", err)
	}
}
```

```go
// go.mod
module github.com/example/microservice

go 1.22
```

---

### 5. 环境变量与配置管理

#### 5.1 配置管理策略

```
配置管理层次:

┌─────────────────────────────────────────────┐
│  Level 4: 运行时配置 (最高优先级)             │
│  - Kubernetes ConfigMap/Secret               │
│  - 环境变量注入                               │
│  - 命令行参数                                │
├─────────────────────────────────────────────┤
│  Level 3: 构建时配置                          │
│  - ARG 指令                                  │
│  - 构建上下文变量                             │
├─────────────────────────────────────────────┤
│  Level 2: 镜像内配置                          │
│  - 配置文件 COPY                             │
│  - 默认环境变量                              │
├─────────────────────────────────────────────┤
│  Level 1: 基础镜像默认配置 (最低优先级)       │
│  - Dockerfile ENV                            │
│  - 基础镜像默认值                            │
└─────────────────────────────────────────────┘

优先级: Level 4 > Level 3 > Level 2 > Level 1
```

#### 5.2 .env 文件管理

```bash
# .env (不提交到 git)
APP_ENV=production
APP_DEBUG=false
APP_NAME=My Application
APP_VERSION=2.1.0

# 数据库
DB_HOST=mysql
DB_PORT=3306
DB_NAME=myapp
DB_USER=app
DB_PASSWORD=strong_random_password_here
MYSQL_ROOT_PASSWORD=root_password_here

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_here

# 应用配置
HTTP_PORT=80
LOG_LEVEL=info
```

```bash
# .env.example (提交到 git，作为模板)
APP_ENV=production
APP_DEBUG=false
APP_NAME=My Application
APP_VERSION=1.0.0
DB_HOST=mysql
DB_PORT=3306
DB_NAME=myapp
DB_USER=app
DB_PASSWORD=CHANGE_ME
MYSQL_ROOT_PASSWORD=CHANGE_ME
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME
HTTP_PORT=80
LOG_LEVEL=info
```

#### 5.3 Dockerfile 中的环境变量

```dockerfile
# ARG vs ENV 的区别
# ARG: 仅在构建时可用，运行时不存在
ARG BUILD_VERSION=1.0.0
ARG BUILD_DATE

# ENV: 构建时和运行时都可用
ENV APP_NAME=MyApp
ENV APP_ENV=production

# 在构建时注入
# docker build --build-arg BUILD_VERSION=2.0.0 --build-arg BUILD_DATE=$(date -u +%Y-%m-%d) .

# 最佳实践: 使用 ARG 注入构建信息
ARG VERSION=dev
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
```

---

### 6. 多服务编排实战

#### 6.1 完整的微服务架构

```yaml
# docker-compose.yml - 完整微服务编排
services:
  # === 反向代理 ===
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "${HTTP_PORT:-80}:80"
      - "${HTTPS_PORT:-443}:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      api:
        condition: service_healthy
      web:
        condition: service_healthy
    networks:
      - frontend
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # === 前端应用 ===
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
      args:
        - NODE_ENV=production
        - API_URL=/api
    networks:
      - frontend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # === API 服务 ===
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    environment:
      - APP_ENV=${APP_ENV:-production}
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_NAME=${DB_NAME:-app}
      - DB_USER=${DB_USER:-app}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - RABBITMQ_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672/
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - frontend
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  # === Worker 进程 ===
  worker:
    build:
      context: ./api
      dockerfile: Dockerfile
    command: ["python", "worker.py"]
    environment:
      - DB_HOST=mysql
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - RABBITMQ_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672/
    depends_on:
      mysql:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - backend
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # === 数据库 ===
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME:-app}
      MYSQL_USER: ${DB_USER:-app}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  # === 缓存 ===
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 384M

  # === 消息队列 ===
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-app}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  mysql_data:
  redis_data:
  rabbitmq_data:
```

---

## 💻 实战练习

### 练习 1: 部署 Flask + Redis 访客计数器

**目标:** 完整部署一个 Flask 应用，使用 Redis 计数，Nginx 反向代理。

```bash
# 创建项目目录
mkdir -p flask-visitor-counter/{nginx,app}
cd flask-visitor-counter

# 创建 Flask 应用 (如上文 app.py 代码)
# 创建 requirements.txt
# 创建 Dockerfile
# 创建 Nginx 配置
# 创建 docker-compose.yml

# 部署
docker compose up -d --build

# 验证
curl http://localhost/health
curl http://localhost/
curl http://localhost/  # 访问计数递增

# 查看日志
docker compose logs -f api

# 清理
docker compose down -v
```

### 练习 2: Node.js 微服务 + MongoDB

**目标:** 部署 Node.js API 服务，连接 MongoDB，实现基本的 CRUD。

```bash
# 创建项目
mkdir -p node-mongo-api
cd node-mongo-api

# 创建 Node.js 应用
# 创建 Dockerfile (多阶段构建)
# 创建 docker-compose.yml

# 部署并测试
docker compose up -d --build

# 测试 API
curl -X POST http://localhost:3000/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "test item", "value": 42}'

curl http://localhost:3000/api/items

# 清理
docker compose down -v
```

### 练习 3: 多服务应用排错

**目标:** 诊断一个故意包含错误的多服务环境。

```bash
# 创建包含以下错误的环境:
# 1. 数据库密码不匹配
# 2. 服务启动顺序问题
# 3. 网络配置错误
# 4. 环境变量缺失

# 排查任务:
# 1. 找出为什么 API 无法连接数据库
# 2. 找出为什么健康检查失败
# 3. 修复所有问题并验证

# 提示命令:
docker compose logs api
docker compose exec api env | grep DB
docker compose exec api ping mysql
docker compose exec mysql mysql -u root -p -e "SELECT 1"
```

---

## 🎯 面试题精选

### 1. Docker 化 Web 应用时，如何选择基础镜像？

**参考答案:**

选择基础镜像需要权衡大小、安全性和兼容性:
- **alpine**: 体积最小(~5MB)，但使用 musl libc 可能导致兼容性问题，适合 Go 等静态编译语言
- **slim**: 基于 Debian 的精简版(~80MB)，兼容性好，适合 Python/Node.js/Java
- **distroless**: Google 出品(~20MB)，只包含运行时，安全性最高
- **scratch**: 空镜像，适合 Go 静态编译的二进制

推荐策略: Go 用 scratch/alpine，Python/Node.js 用 slim，Java 用 distroless。

### 2. 为什么生产环境不用 `python app.py` 而用 gunicorn/uwsgi？

**参考答案:**

`python app.py` 启动的是 Flask 内置的开发服务器，是单线程的，不适合生产:
- **性能差**: 单线程处理请求，无法处理并发
- **不稳定**: 没有进程管理，崩溃后不会自动重启
- **不安全**: 调试模式会暴露敏感信息

gunicorn 是 WSGI HTTP 服务器，支持多 worker 进程和多线程，内置进程管理、优雅关闭等生产级特性。

### 3. 多阶段构建的优势是什么？举一个实际例子。

**参考答案:**

多阶段构建将构建环境和运行环境分离:
- **优势 1**: 镜像体积大幅减小（构建工具、源码不进入最终镜像）
- **优势 2**: 减少攻击面（编译器、调试工具不在生产镜像中）
- **优势 3**: 保护知识产权（源码不包含在最终镜像中）

例如 Go 应用: 第一阶段用 golang:1.22 编译得到静态二进制，第二阶段仅将二进制复制到 scratch 镜像，最终镜像从 ~800MB 缩小到 ~10MB。

### 4. 如何处理 Docker 容器中的配置文件？

**参考答案:**

按优先级从高到低:
1. **环境变量**: 适合简单配置，通过 docker-compose environment 或 K8s ConfigMap 注入
2. **配置文件挂载**: 通过 volume 挂载配置文件（`-v ./config.yaml:/app/config.yaml:ro`）
3. **Docker secrets**: 敏感信息（密码、密钥）通过 Docker secrets 或 K8s Secrets 管理
4. **镜像内默认值**: Dockerfile 中 COPY 默认配置文件

最佳实践: 代码读取环境变量 > 读取配置文件 > 使用默认值。

### 5. docker-compose 中 depends_on 和 condition 的关系是什么？

**参考答案:**

`depends_on` 控制启动顺序，但默认只保证容器"已启动"，不保证"已就绪"。`condition` 可以指定更严格的条件:
- `service_started`: 默认行为，容器启动即可
- `service_healthy`: 等待健康检查通过（需要配置 healthcheck）
- `service_completed_successfully`: 等待容器正常退出

生产环境推荐使用 `service_healthy` 配合 healthcheck，确保依赖服务真正可用后再启动下游服务。

### 6. 如何优化 Docker 化 Web 应用的启动时间？

**参考答案:**

1. **镜像层缓存**: 将不常变化的层（依赖安装）放在前面，利用 Docker 构建缓存
2. **精简基础镜像**: 使用 alpine 或 slim 减少下载时间
3. **减少层数**: 合并 RUN 指令
4. **预热缓存**: 预拉取基础镜像到所有节点
5. **并行构建**: 使用 BuildKit 的并行构建能力
6. **依赖缓存**: 使用 `--mount=type=cache` 缓存包管理器缓存目录
7. **健康检查调优**: 设置合理的 `start_period` 避免过早判定失败

### 7. 容器化应用的日志应该如何管理？

**参考答案:**

最佳实践:
- 应用将日志输出到 stdout/stderr（而非文件）
- Docker 通过 json-file 或 syslog driver 收集日志
- 使用日志驱动的 `max-size` 和 `max-file` 选项限制日志大小
- 生产环境使用 fluentd/loki driver 将日志发送到集中式日志系统

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```

### 8. 如何实现容器化应用的零停机部署？

**参考答案:**

使用 Docker Compose 的以下策略:
1. 先构建新镜像
2. 使用 `docker compose up -d --no-deps --build <service>` 只更新特定服务
3. 配置 `restart: unless-stopped` 或使用 `deploy.update_config` (Swarm 模式)
4. 配置健康检查确保新容器就绪后再停止旧容器
5. 使用 Nginx upstream 或负载均衡器实现蓝绿部署

对于 Swarm: `docker service update --update-parallelism 1 --update-delay 10s my-service`

### 9. 如何在 Docker 环境中管理应用密钥？

**参考答案:**

1. **Docker Swarm secrets**: 使用 `docker secret create` 管理，挂载到容器的 `/run/secrets/`
2. **环境变量**: 适合非敏感配置，通过 `.env` 文件管理（注意不要提交到 git）
3. **HashiCorp Vault**: 企业级密钥管理，支持动态密钥、自动轮换
4. **Kubernetes Secrets**: K8s 环境中使用，可与 Vault 集成

禁止: 在 Dockerfile 中硬编码密码、在 docker-compose.yml 中明文写密码。

### 10. Docker 化应用的健康检查应该如何设计？

**参考答案:**

健康检查应覆盖所有关键依赖:
- **HTTP 端点**: `/health` 返回应用状态
- **数据库连接**: 验证数据库可连接并可查询
- **缓存连接**: 验证 Redis/Memcached 可用
- **磁盘空间**: 检查磁盘使用率
- **外部依赖**: 检查关键外部 API 可达性

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

注意设置合理的 `start_period`，给应用足够的初始化时间。

---

## 📚 深入阅读

- [Docker 官方示例应用](https://docs.docker.com/samples/)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Nginx Docker 官方镜像](https://hub.docker.com/_/nginx)
- [PHP Docker 官方镜像](https://hub.docker.com/_/php)
- [Node.js Docker 最佳实践](https://nodejs.org/en/learn/getting-started/nodejs-with-docker)
- [Go Docker 官方镜像](https://hub.docker.com/_/golang)
- [Python Docker 官方镜像](https://hub.docker.com/_/python)

---

## ✅ 自检清单

- [ ] 能独立编写 Nginx + PHP-FPM 的多容器应用
- [ ] 能使用多阶段构建优化 Node.js/Go 镜像
- [ ] 理解 Python WSGI 服务器（gunicorn）的配置
- [ ] 能使用环境变量和 .env 文件管理配置
- [ ] 理解 docker-compose 中的服务依赖和健康检查
- [ ] 能设计合理的网络隔离方案（frontend/backend）
- [ ] 理解容器日志的最佳实践（stdout/stderr）
- [ ] 能配置资源限制（CPU/内存）
- [ ] 理解非 root 用户运行容器的原因和方法
- [ ] 能排查容器化应用的常见问题
