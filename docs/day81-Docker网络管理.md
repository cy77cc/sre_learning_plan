# Day 81: Docker 网络管理

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 网络管理
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Docker 网络驱动类型
- 掌握 bridge、host、none 网络的区别
- 能创建自定义网络实现容器间通信
- 理解端口映射原理

---

## 📖 Docker 网络驱动

### 1. 网络驱动类型

| 驱动 | 说明 | 适用场景 |
|------|------|---------|
| bridge | 默认驱动，容器间隔离 | 单机容器通信 |
| host | 使用宿主机网络 | 高性能场景 |
| none | 无网络 | 安全隔离 |
| overlay | 跨主机网络 | Swarm 集群 |
| macvlan | 直接分配 MAC 地址 | 需要独立 IP |

### 2. Bridge 网络（默认）

```bash
# 查看网络
docker network ls

# 默认 bridge 网络
docker network inspect bridge

# 创建自定义 bridge 网络
docker network create mynet

# 运行容器加入网络
docker run -d --name web --network mynet nginx
docker run -d --name db --network mynet mysql

# 容器间通过名称通信
docker exec web ping db
```

### 3. Host 网络

```bash
docker run -d --network host nginx
# 容器直接使用宿主机 IP 和端口
# 无需 -p 端口映射
```

### 4. None 网络

```bash
docker run -d --network none alpine sleep 3600
# 容器没有网络接口（只有 lo）
```

### 5. 端口映射

```bash
# 映射到宿主机
docker run -p 8080:80 nginx        # 宿主机:容器
docker run -p 127.0.0.1:8080:80 nginx  # 绑定特定 IP
docker run -p 8080:80/tcp -p 8443:443/tcp nginx

# 端口范围
docker run -p 8000-8010:8000-8010 nginx

# 动态端口
docker run -P nginx    # 自动映射到随机端口
```

### 6. DNS 与容器发现

```
自定义 bridge 网络的 DNS 特性：
- 容器可通过名称互相解析
- 默认 bridge 网络不支持名称解析
- 自定义网络内置 DNS 服务器

docker network create mynet
docker run -d --name app1 --network mynet nginx
docker run -d --name app2 --network mynet redis
docker exec app1 ping app2    # ✅ 可解析
```

### 7. 网络故障排查

```bash
# 查看网络
docker network ls
docker network inspect mynet

# 查看容器网络
docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' myapp

# 测试连通性
docker exec myapp ping other-container
docker exec myapp curl http://other-container:80

# 清理
docker network prune
```

---

## 📚 扩展阅读

- [Docker 网络文档](https://docs.docker.com/network/)
- [Bridge 网络详解](https://docs.docker.com/network/bridge/)
