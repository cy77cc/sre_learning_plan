# Day 89: Docker 阶段测试

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 阶段测试：多容器应用部署 + 安全扫描
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合运用 Docker 知识完成项目
- 掌握容器安全扫描
- 能排查 Docker 常见问题

---

## 🏗️ 综合项目

### 部署完整 Web 栈

```bash
# 1. 创建项目结构
mkdir -p webapp/{nginx,app,db}

# 2. 编写 docker-compose.yml
# 3. 构建并启动
docker compose up -d --build

# 4. 验证
docker compose ps
docker compose logs
curl http://localhost
```

### 安全扫描

```bash
# Trivy 扫描
trivy image myapp:latest

# 检查 Dockerfile
docker scout cve myapp:latest

# 检查配置
docker bench security
```

### 常见故障排查

```bash
# 容器无法启动
docker logs <container>

# 网络不通
docker exec <container> ping <other>

# 磁盘满
docker system df
docker system prune -a
```

---

## 📚 扩展阅读

- [Docker 故障排查指南](https://docs.docker.com/config/containers/troubleshoot/)
