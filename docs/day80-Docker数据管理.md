     1|# Day 80: Docker 数据管理
     2|
     3|> 📅 日期：2026-05-03
     4|> 📖 学习主题：Docker 数据管理
     5|> ⏰ 计划学习时间：2-3 小时
     6|
     7|---
     8|
     9|## 🎯 学习目标
    10|
    11|- 理解 Volume vs Bind Mount vs tmpfs
    12|- 掌握 Docker Volume 的创建和管理
    13|- 能正确持久化容器数据
    14|
    15|---
    16|
    17|## 📖 数据存储方式
    18|
    19|| 类型 | 存储位置 | 持久化 | 性能 | 适用场景 |
    20||------|---------|--------|------|---------|
    21|| Volume | Docker 管理 | ✅ | 高 | 数据库、应用数据 |
    22|| Bind Mount | 宿主机路径 | ✅ | 高 | 开发时挂载代码 |
    23|| tmpfs | 内存 | ❌ | 最高 | 临时数据、缓存 |
    24|
    25|### 1. Docker Volume
    26|
    27|```bash
    28|docker volume create mydata
    29|docker volume ls
    30|docker volume inspect mydata
    31|docker run -v mydata:/var/lib/mysql mysql
    32|docker volume rm mydata
    33|docker volume prune
    34|```
    35|
    36|### 2. Bind Mount
    37|
    38|```bash
    39|docker run -v /host/path:/container/path nginx
    40|docker run -v /host/path:/container/path:ro nginx
    41|docker run -v /host/nginx.conf:/etc/nginx/nginx.conf nginx
    42|```
    43|
    44|### 3. tmpfs
    45|
    46|```bash
    47|docker run --tmpfs /tmp nginx
    48|docker run --tmpfs /tmp:rw,size=100m nginx
    49|```
    50|
    51|### 4. 备份与恢复
    52|
    53|```bash
    54|# 备份
    55|docker run --rm -v mydata:/data -v $(pwd):/backup alpine \
    56|    tar czf /backup/mydata-backup.tar.gz -C /data .
    57|
    58|# 恢复
    59|docker run --rm -v mydata:/data -v $(pwd):/backup alpine \
    60|    tar xzf /backup/mydata-backup.tar.gz -C /data
    61|```
    62|
    63|### 5. docker-compose 示例
    64|
    65|```yaml
    66|version: '3.8'
    67|services:
    68|  mysql:
    69|    image: mysql:8.0
    70|    environment:
    71|      MYSQL_ROOT_PASSWORD: secret
    72|    volumes:
    73|      - mysql_data:/var/lib/mysql
    74|    ports:
    75|      - "3306:3306"
    76|
    77|  redis:
    78|    image: redis:7-alpine
    79|    volumes:
    80|      - redis_data:/data
    81|
    82|volumes:
    83|  mysql_data:
    84|  redis_data:
    85|```
    86|
    87|---
    88|
    89|## 📚 扩展阅读
    90|
    91|- [Docker 存储文档](https://docs.docker.com/storage/)
    92|- [Volume vs Bind Mount](https://docs.docker.com/storage/volumes/)
    93|

## 6. 权限问题

```bash
# 用户映射
docker run -v /host/data:/data -u $(id -u):$(id -g) myapp

# 修复权限
docker run --rm -v mydata:/data alpine chown -R 1000:1000 /data
```

## 7. Volume 驱动

```bash
docker volume create --driver local \
    --opt type=nfs \
    --opt o=addr=10.0.1.100,rw \
    --opt device=:/exports/data \
    nfs_volume
```

## 8. 完整 docker-compose

```yaml
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: myapp
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  app:
    build: .
    environment:
      - DB_HOST=mysql
      - REDIS_HOST=redis
    volumes:
      - app_logs:/app/logs
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  mysql_data:
  redis_data:
  app_logs:
```

---

## 📚 扩展阅读

- [Docker 存储文档](https://docs.docker.com/storage/)
- [Volume vs Bind Mount](https://docs.docker.com/storage/volumes/)
