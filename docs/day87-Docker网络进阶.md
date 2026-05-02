# Day 87: Docker 网络进阶

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 网络进阶
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Overlay 网络
- 掌握 macvlan 网络
- 能调试 Docker 网络问题

---

## 📖 进阶网络

### 1. Overlay 网络

```bash
# 用于 Swarm 集群跨主机通信
docker network create --driver overlay my-overlay

# 特性：
# - 跨主机容器可直接通信
# - 自动加密
# - 基于 VXLAN
```

### 2. Macvlan 网络

```bash
docker network create -d macvlan \
    --subnet=192.168.1.0/24 \
    --gateway=192.168.1.1 \
    -o parent=eth0 \
    macvlan-net

docker run -d --network macvlan-net nginx
# 容器获得独立的 MAC 和 IP
```

### 3. 网络故障排查

```bash
# 查看网络命名空间
docker inspect --format '{{.NetworkSettings.SandboxKey}}' myapp

# 进入网络命名空间
nsenter --net=$(docker inspect -f '{{.NetworkSettings.SandboxKey}}' myapp)

# 抓包
tcpdump -i docker0 -n
```

---

## 📚 扩展阅读

- [Docker 网络驱动](https://docs.docker.com/network/)
- [Overlay 网络](https://docs.docker.com/network/overlay/)
