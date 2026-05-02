# Day 83: Dockerfile 最佳实践

> 📅 日期：2026-05-03
> 📖 学习主题：Dockerfile 最佳实践
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握编写高效 Dockerfile 的原则
- 理解安全最佳实践
- 能优化镜像大小和构建速度

---

## 📖 最佳实践

### 1. 选择精简基础镜像

```
推荐：
  alpine（~5MB）— 最小，但 musl libc 可能有兼容问题
  debian-slim（~80MB）— 平衡大小和兼容性
  distroless（~20MB）— Google 出品，只包含运行时

不推荐：
  ubuntu（~77MB）— 包含很多不必要的包
  python:latest（~900MB）— 完整开发环境
```

### 2. 利用构建缓存

```dockerfile
# 将不变的指令放前面
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### 3. 多阶段构建

```dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

### 4. 安全实践

```dockerfile
# 不用 root 运行
RUN useradd -r -s /bin/false appuser
USER appuser

# 不暴露敏感信息
# 不要用 ENV 存密码
# 用 --secret 或 Docker secrets

# 扫描漏洞
docker scout cve myimage:latest
```

### 5. .dockerignore

```
.git
node_modules
__pycache__
*.pyc
.env
Dockerfile
.dockerignore
```

---

## 📚 扩展阅读

- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
