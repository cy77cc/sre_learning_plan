# Day 84: Docker Compose 多容器编排

> 📅 日期：2026-05-03
> 📖 学习主题：Docker Compose 多容器编排
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 docker-compose.yml 语法
- 能用 Compose 管理多容器应用
- 理解 Compose 的启动顺序和依赖管理

---

## 📖 Compose 基础

### 1. 核心概念

```yaml
version: '3.8'
services:       # 定义容器
  web:
    build: .
    ports:
      - "80:80"
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: secret
volumes:        # 定义数据卷
  db_data:
networks:       # 定义网络
  appnet:
```

### 2. 常用指令

```yaml
services:
  app:
    build: .              # 从 Dockerfile 构建
    image: myapp:v1       # 或使用现成镜像
    ports:
      - "8080:80"         # 端口映射
    environment:          # 环境变量
      - DB_HOST=db
      - DB_PORT=3306
    env_file:             # 从文件加载
      - .env
    volumes:              # 数据挂载
      - ./data:/app/data
      - logs:/app/logs
    depends_on:           # 依赖
      db:
        condition: service_healthy
    networks:
      - appnet
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### 3. 常用命令

```bash
docker compose up -d           # 启动
docker compose down            # 停止并删除
docker compose ps              # 查看状态
docker compose logs -f app     # 查看日志
docker compose exec app bash   # 进入容器
docker compose build           # 重新构建
docker compose pull            # 拉取镜像
docker compose restart app     # 重启单个服务
```

### 4. Profile

```yaml
services:
  app:
    build: .
  debug:
    image: myapp:debug
    profiles: ["debug"]
```

```bash
docker compose up -d              # 不启动 debug
docker compose --profile debug up # 启动 debug
```

---

## 📚 扩展阅读

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Compose 文件参考](https://docs.docker.com/compose/compose-file/)
