# Day 76: Docker 简介与安装

> 📅 日期：2026-05-02  
> 📖 学习主题：Docker 简介与安装  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 76 的学习后，你应该掌握：
- 理解 Docker 简介与安装 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Docker 核心概念

#### 1.1 容器 vs 虚拟机

```
┌──────────────────────────┐  ┌──────────────────────────┐
│     虚拟机 (VM)           │  │      容器 (Container)     │
├──────────────────────────┤  ├──────────────────────────┤
│   App  App  App          │  │   App  App  App          │
│   Libs Libs Libs         │  │   Libs Libs Libs         │
├──────────────────────────┤  ├──────────────────────────┤
│     Guest OS (完整)       │  │   Docker Engine          │
├──────────────────────────┤  ├──────────────────────────┤
│       Hypervisor          │  │     Host OS (共享内核)    │
├──────────────────────────┤  ├──────────────────────────┤
│     Host OS              │  │     Host OS              │
├──────────────────────────┤  ├──────────────────────────┤
│     硬件                 │  │     硬件                 │
└──────────────────────────┘  └──────────────────────────┘

VM:       启动 1-3 分钟，占用 GB 级内存，强隔离
Container: 启动毫秒级，占用 MB 级内存，进程级隔离
```

#### 1.2 Docker 架构

```
┌──────────┐      REST API     ┌──────────────┐
│  Docker  │  ──────────────→  │   Docker     │
│   CLI    │                   │   Daemon     │
│ (docker) │  ←──────────────  │  (dockerd)   │
└──────────┘                   └──────┬───────┘
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                    ┌──────┐  ┌──────┐  ┌──────┐
                    │Image │  │Cont. │  │ Vol. │
                    └──────┘  └──────┘  └──────┘
```

### 2. 安装 Docker

```bash
# Ubuntu 官方方式
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 免 sudo 使用
sudo usermod -aG docker $USER
# 退出重新登录生效

# 设置开机启动
sudo systemctl enable docker
sudo systemctl start docker

# 验证
docker run hello-world
```

### 3. Docker 基础命令

```bash
# 查看版本
docker version
docker info

# 镜像操作
docker pull ubuntu:22.04
docker images
docker rmi ubuntu:22.04

# 容器操作
docker run -it ubuntu:22.04 bash
docker run -d -p 8080:80 nginx
docker ps
docker ps -a
docker stop <container_id>
docker rm <container_id>
docker logs -f <container_id>
docker exec -it <container_id> bash

# 系统清理
docker system df       # 查看磁盘使用
docker system prune    # 清理未使用的资源
```

### 4. SRE 实战

```
场景：服务器磁盘满
排查：
1. docker system df — 发现 images 占 50GB
2. docker image ls — 大量未使用的旧镜像
3. docker system prune -a — 清理所有未使用的镜像
4. 长期：配置镜像清理 cron + 镜像大小限制
```


---

## 💻 实战练习

### 练习 1：多阶段构建优化

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp

# Runtime stage
FROM alpine:3.18
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/myapp /usr/local/bin/myapp
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -qO- http://localhost:8080/health || exit 1
CMD ["myapp"]
```

### 练习 2：docker-compose 编排

```yaml
version: "3.8"
services:
  web:
    build: .
    ports: ["8080:8080"]
    depends_on: [db, redis]
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379
  db:
    image: postgres:15-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
volumes:
  pgdata:
```


---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-05-02 15:29:18*  
*Generated by Hermes Agent with review*
