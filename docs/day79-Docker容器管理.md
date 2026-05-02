     1|# Day 79: Docker 容器管理
     2|
     3|> 📅 日期：2026-05-03
     4|> 📖 学习主题：Docker 容器管理
     5|> ⏰ 计划学习时间：2-3 小时
     6|
     7|---
     8|
     9|## 🎯 学习目标
    10|
    11|- 掌握容器的生命周期管理
    12|- 理解容器资源限制
    13|- 能进入容器进行调试
    14|- 掌握容器日志管理
    15|
    16|---
    17|
    18|## 📖 容器生命周期
    19|
    20|```
    21|创建 → 运行 → 停止 → 删除
    22|  │       │      │
    23|  │       │      └─ docker stop (SIGTERM → 10s → SIGKILL)
    24|  │       │
    25|  │       ├─ docker pause (冻结进程)
    26|  │       │
    27|  │       └─ docker restart
    28|```
    29|
    30|### 1. 基本操作
    31|
    32|```bash
    33|# 创建并运行
    34|docker run --name myapp -d -p 8080:80 nginx
    35|
    36|# 常用选项
    37|docker run \
    38|    --name myapp \
    39|    -d \
    40|    -p 8080:80 \
    41|    -v /data:/app/data \
    42|    -e DB_HOST=db \
    43|    --restart unless-stopped \
    44|    nginx:latest
    45|
    46|# 查看容器
    47|docker ps
    48|docker ps -a
    49|
    50|# 停止/启动
    51|docker stop myapp
    52|docker start myapp
    53|docker restart myapp
    54|
    55|# 删除
    56|docker rm myapp
    57|docker rm -f myapp
    58|
    59|# 日志
    60|docker logs myapp
    61|docker logs -f myapp
    62|docker logs --tail 100 myapp
    63|
    64|# 进入容器
    65|docker exec -it myapp /bin/bash
    66|docker exec myapp ls /app
    67|```
    68|
    69|### 2. 资源限制
    70|
    71|```bash
    72|# CPU
    73|docker run --cpus="1.5" nginx
    74|docker run --cpuset-cpus="0,1" nginx
    75|
    76|# 内存
    77|docker run --memory="512m" nginx
    78|
    79|# 查看
    80|docker stats
    81|docker stats myapp
    82|```
    83|
    84|### 3. 调试技巧
    85|
    86|```bash
    87|# 查看进程
    88|docker top myapp
    89|
    90|# 查看变更
    91|docker diff myapp
    92|
    93|# 复制文件
    94|docker cp myapp:/etc/nginx/nginx.conf ./
    95|docker cp ./config myapp:/etc/nginx/
    96|
    97|# 暂停/恢复
    98|docker pause myapp
    99|docker unpause myapp
   100|
   101|# 导出/导入
   102|docker export myapp > backup.tar
   103|docker import backup.tar myimage:v1
   104|```
   105|
   106|### 4. 容器网络
   107|
   108|```bash
   109|docker network ls
   110|docker network create mynet
   111|docker run -d --name app1 --network mynet nginx
   112|docker run -d --name app2 --network mynet redis
   113|docker exec app1 ping app2
   114|```
   115|
   116|### 5. 重启策略
   117|
   118|| 策略 | 说明 |
   119||------|------|
   120|| no | 不自动重启 |
   121|| always | 总是重启 |
   122|| unless-stopped | 除非手动停止 |
   123|| on-failure | 失败时重启 |
   124|
   125|```bash
   126|docker run --restart unless-stopped nginx
   127|docker update --restart always myapp
   128|```
   129|
   130|---
   131|
   132|## 📚 扩展阅读
   133|
   134|- [Docker 容器文档](https://docs.docker.com/engine/containers/)
   135|- [Docker 资源限制](https://docs.docker.com/config/containers/resource_constraints/)
   136|

## 6. 批量操作

```bash
# 停止所有
docker stop $(docker ps -q)

# 删除已停止的
docker rm $(docker ps -aq -f status=exited)

# 按名称过滤
docker ps --filter "name=web"
docker ps --filter "label=env=production"
```

## 7. 启动脚本示例

```bash
#!/bin/bash
set -e

# 创建网络
docker network create appnet 2>/dev/null || true

# 启动 Redis
docker run -d --name redis \
    --network appnet \
    --restart unless-stopped \
    redis:7-alpine

# 启动应用
docker run -d --name app \
    --network appnet \
    --restart unless-stopped \
    -p 8080:8080 \
    -e REDIS_HOST=redis \
    myapp:latest

# 启动 Nginx
docker run -d --name nginx \
    --network appnet \
    --restart unless-stopped \
    -p 80:80 \
    -v ./nginx.conf:/etc/nginx/nginx.conf:ro \
    nginx:alpine

echo "All services started"
docker ps --filter "network=appnet"
```

## 8. 监控与告警

```bash
# 持续监控
watch -n 2 'docker stats --no-stream'

# 导出指标
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 检查健康状态
docker inspect --format='{{.State.Health.Status}}' myapp
```

---

## 🧪 练习题

### 练习 1：容器调试

容器启动后立刻退出，如何排查？

<details>
<summary>答案</summary>

```bash
docker ps -a          # 看退出码
docker logs myapp     # 看日志
docker inspect myapp  # 看详情
docker run -it --entrypoint /bin/sh myimage  # 交互式调试
```
</details>

---

## 📚 扩展阅读

- [Docker 容器文档](https://docs.docker.com/engine/containers/)
- [Docker 资源限制](https://docs.docker.com/config/containers/resource_constraints/)
