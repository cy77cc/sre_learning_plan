# Day 85: Docker 私有仓库

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 私有仓库
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解私有仓库的作用
- 能搭建 Docker Registry
- 掌握镜像的推送和拉取

---

## 📖 私有仓库

### 1. 为什么需要私有仓库

- 安全：镜像不暴露在公网
- 速度：内网拉取更快
- 合规：满足企业审计要求
- 控制：自主管理镜像生命周期

### 2. 搭建 Registry

```bash
docker run -d --name registry \
    -p 5000:5000 \
    --restart unless-stopped \
    registry:2
```

### 3. 配置客户端

```bash
# 配置 insecure registry
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "insecure-registries": ["registry.example.com:5000"]
}
EOF
sudo systemctl restart docker
```

### 4. 推送与拉取

```bash
docker tag myapp:latest registry.example.com:5000/myapp:v1
docker push registry.example.com:5000/myapp:v1
docker pull registry.example.com:5000/myapp:v1
```

### 5. Harbor

```bash
# Harbor 是企业级私有仓库
# 支持：RBAC、扫描、复制、垃圾回收
# 安装：
git clone https://github.com/goharbor/harbor.git
cd harbor
cp harbor.yml.tmpl harbor.yml
./install.sh
```

---

## 📚 扩展阅读

- [Docker Registry 文档](https://docs.docker.com/registry/)
- [Harbor 官网](https://goharbor.io/)
