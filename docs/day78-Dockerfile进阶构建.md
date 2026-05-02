     1|# Day 78: Dockerfile 进阶构建
     2|
     3|> 📅 日期：2026-05-03
     4|> 📖 学习主题：Dockerfile 进阶构建
     5|> ⏰ 计划学习时间：2-3 小时
     6|
     7|---
     8|
     9|## 🎯 学习目标
    10|
    11|- 掌握 Dockerfile 所有常用指令
    12|- 理解构建缓存机制
    13|- 能编写生产级 Dockerfile
    14|- 掌握多阶段构建
    15|
    16|---
    17|
    18|## 📖 Dockerfile 指令
    19|
    20|### 1. 基础指令
    21|
    22|| 指令 | 用途 | 示例 |
    23||------|------|------|
    24|| FROM | 指定基础镜像 | `FROM python:3.11-slim` |
    25|| RUN | 执行命令 | `RUN apt-get update` |
    26|| COPY | 复制文件 | `COPY app.py /app/` |
    27|| ADD | 复制文件（支持 URL/tar） | `ADD https://... /tmp/` |
    28|| WORKDIR | 设置工作目录 | `WORKDIR /app` |
    29|| EXPOSE | 声明端口 | `EXPOSE 8080` |
    30|| ENV | 设置环境变量 | `ENV NODE_ENV=production` |
    31|| CMD | 默认启动命令 | `CMD ["python", "app.py"]` |
    32|| ENTRYPOINT | 入口点 | `ENTRYPOINT ["nginx"]` |
    33|| USER | 切换用户 | `USER nobody` |
    34|| VOLUME | 声明挂载点 | `VOLUME /data` |
    35|| ARG | 构建参数 | `ARG VERSION=latest` |
    36|| LABEL | 添加元数据 | `LABEL maintainer="team@example.com"` |
    37|
    38|### 2. CMD vs ENTRYPOINT
    39|
    40|```dockerfile
    41|# CMD — 可被 docker run 覆盖
    42|FROM ubuntu
    43|CMD ["echo", "hello"]
    44|# docker run myimage          → 输出 hello
    45|# docker run myimage echo hi  → 输出 hi
    46|
    47|# ENTRYPOINT — 不可被覆盖
    48|FROM ubuntu
    49|ENTRYPOINT ["echo"]
    50|CMD ["hello"]
    51|# docker run myimage          → 输出 hello
    52|# docker run myimage hi       → 输出 hi
    53|
    54|# 组合使用（推荐）
    55|ENTRYPOINT ["python"]
    56|CMD ["app.py"]
    57|```
    58|
    59|### 3. 多阶段构建
    60|
    61|```dockerfile
    62|# Stage 1: Build
    63|FROM golang:1.21 AS builder
    64|WORKDIR /app
    65|COPY go.mod go.sum ./
    66|RUN go mod download
    67|COPY . .
    68|RUN CGO_ENABLED=0 go build -o /myapp
    69|
    70|# Stage 2: Run
    71|FROM alpine:3.18
    72|RUN apk --no-cache add ca-certificates
    73|COPY --from=builder /myapp /myapp
    74|EXPOSE 8080
    75|ENTRYPOINT ["/myapp"]
    76|```
    77|
    78|### 4. 构建缓存优化
    79|
    80|```dockerfile
    81|# ❌ 缓存经常失效
    82|COPY . /app
    83|RUN pip install -r requirements.txt
    84|
    85|# ✅ 先复制依赖文件
    86|COPY requirements.txt .
    87|RUN pip install --no-cache-dir -r requirements.txt
    88|COPY . /app
    89|```
    90|
    91|### 5. 生产级 Dockerfile 示例
    92|
    93|```dockerfile
    94|FROM python:3.11-slim AS base
    95|
    96|LABEL maintainer="sre-team@example.com"
    97|LABEL version="1.0"
    98|
    99|ENV PYTHONDONTWRITEBYTECODE=1 \
   100|    PYTHONUNBUFFERED=1 \
   101|    PIP_NO_CACHE_DIR=1
   102|
   103|WORKDIR /app
   104|
   105|FROM base AS builder
   106|COPY requirements.txt .
   107|RUN pip wheel --no-cache-dir -w /wheels -r requirements.txt
   108|
   109|FROM base AS runtime
   110|COPY --from=builder /wheels /wheels
   111|RUN pip install --no-cache-dir /wheels/*
   112|COPY . /app
   113|
   114|RUN useradd -r -s /bin/false appuser \
   115|    && chown -R appuser:appuser /app
   116|
   117|USER appuser
   118|EXPOSE 8080
   119|
   120|HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
   121|    CMD curl -f http://localhost:8080/health || exit 1
   122|
   123|CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   124|```
   125|
   126|---
   127|
   128|## 📚 扩展阅读
   129|
   130|- [Dockerfile 参考](https://docs.docker.com/engine/reference/builder/)
   131|- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
   132|

## 5. ONBUILD 指令

```dockerfile
FROM node:18
ONBUILD COPY . /app
ONBUILD RUN npm install
```

## 6. SHELL 指令

```dockerfile
FROM ubuntu:22.04
SHELL ["/bin/bash", "-c"]
RUN source /opt/app/env && npm install
```

## 7. HEALTHCHECK 指令

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
HEALTHCHECK NONE
```

## 8. 生产级模板

### Go
```dockerfile
FROM golang:1.21-alpine AS builder
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server .

FROM alpine:3.18
RUN apk --no-cache add ca-certificates
COPY --from=builder /server /server
USER nobody
EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Node.js
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

### Java
```dockerfile
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn package -DskipTests

FROM eclipse-temurin:17-jre-alpine
COPY --from=builder /app/target/*.jar /app.jar
USER nobody
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

---

## 🧪 练习题

### 练习 1：编写 Rust Dockerfile

<details>
<summary>答案</summary>

```dockerfile
FROM rust:1.72 AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main(){}" > src/main.rs
RUN cargo build --release
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/myapp /myapp
EXPOSE 8080
ENTRYPOINT ["/myapp"]
```
</details>

---

## 📚 扩展阅读

- [Dockerfile 参考](https://docs.docker.com/engine/reference/builder/)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
