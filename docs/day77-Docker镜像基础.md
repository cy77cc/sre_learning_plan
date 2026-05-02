     1|# Day 77: Docker 镜像基础
     2|
     3|> 📅 日期：2026-05-03
     4|> 📖 学习主题：Docker 镜像基础
     5|> ⏰ 计划学习时间：2-3 小时
     6|
     7|---
     8|
     9|## 🎯 学习目标
    10|
    11|- 理解 Docker 镜像的分层存储机制
    12|- 掌握镜像的拉取、查看、删除操作
    13|- 能构建自定义镜像
    14|- 理解镜像标签和版本管理
    15|
    16|---
    17|
    18|## 📖 详细知识点
    19|
    20|### 1. 镜像分层存储
    21|
    22|```
    23|Docker 镜像由多层只读层叠加而成：
    24|
    25|FROM ubuntu:22.04          ← 基础层 (~77MB)
    26|RUN apt update             ← 层 2
    27|RUN apt install -y python3 ← 层 3
    28|COPY app.py /app/          ← 层 4
    29|CMD ["python3", "/app/app.py"] ← 层 5
    30|
    31|优势：
    32|- 层可复用：多个镜像共享相同基础层
    33|- 节省存储：相同层只存一份
    34|- 加速构建：未变化的层使用缓存
    35|- 缓存失效：某层变化后，后续所有层重新构建
    36|```
    37|
    38|### 2. 镜像操作命令
    39|
    40|```bash
    41|# 拉取镜像
    42|docker pull python:3.11-slim
    43|docker pull nginx:latest
    44|docker pull redis:7-alpine
    45|
    46|# 查看本地镜像
    47|docker images
    48|docker images -a          # 包含中间层
    49|docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    50|
    51|# 搜索镜像
    52|docker search nginx
    53|docker search --filter "is-official=true" python
    54|
    55|# 查看镜像详情
    56|docker inspect python:3.11-slim
    57|docker history python:3.11-slim
    58|
    59|# 删除镜像
    60|docker rmi python:3.11-slim
    61|docker rmi $(docker images -q)    # 删除所有
    62|
    63|# 清理未使用的镜像
    64|docker system prune -a
    65|docker system df
    66|```
    67|
    68|### 3. 镜像标签与版本
    69|
    70|```
    71|镜像命名规范：
    72|  [registry/][namespace/]name[:tag]
    73|
    74|示例：
    75|  nginx:latest            ← Docker Hub 官方镜像
    76|  myuser/myapp:v1.2.3     ← 用户自定义镜像
    77|  registry.example.com/myapp:v1  ← 私有仓库
    78|
    79|常用标签约定：
    80|  latest      ← 最新稳定版（不推荐用于生产）
    81|  1.0         ← 主版本
    82|  1.0.3       ← 具体版本
    83|  alpine      ← 基于 Alpine 的精简版
    84|  slim        ← 基于 Debian slim 的精简版
    85|```
    86|
    87|### 4. 镜像大小对比
    88|
    89|| 镜像 | 大小 | 说明 |
    90||------|------|------|
    91|| ubuntu:22.04 | ~77MB | 完整 Ubuntu |
    92|| debian:bookworm-slim | ~80MB | 精简 Debian |
    93|| alpine:3.18 | ~7MB | 极简 Linux |
    94|| python:3.11 | ~920MB | 完整 Python |
    95|| python:3.11-slim | ~120MB | 精简 Python |
    96|| python:3.11-alpine | ~50MB | Alpine Python |
    97|
    98|### 5. 仓库操作
    99|
   100|```bash
   101|# 登录
   102|docker login
   103|docker login registry.example.com
   104|
   105|# 打标签
   106|docker tag myapp:v1 myuser/myapp:v1
   107|
   108|# 推送
   109|docker push myuser/myapp:v1
   110|
   111|# 推送私有仓库
   112|docker tag myapp:v1 registry.example.com/myapp:v1
   113|docker push registry.example.com/myapp:v1
   114|
   115|# 导出/导入
   116|docker save myapp:v1 -o myapp.tar
   117|docker load -i myapp.tar
   118|```
   119|
   120|### 6. 构建缓存与优化
   121|
   122|```bash
   123|# 不使用缓存
   124|docker build --no-cache -t myapp:v2 .
   125|
   126|# 使用构建参数
   127|docker build --build-arg VERSION=1.2.3 -t myapp:v1.2.3 .
   128|
   129|# BuildKit
   130|DOCKER_BUILDKIT=1 docker build -t myapp:v1 .
   131|```
   132|
   133|### 7. 实战：构建 Python 应用镜像
   134|
   135|```dockerfile
   136|FROM python:3.11-slim
   137|
   138|LABEL maintainer="sre@example.com"
   139|
   140|ENV PYTHONDONTWRITEBYTECODE=1
   141|ENV PYTHONUNBUFFERED=1
   142|
   143|WORKDIR /app
   144|
   145|COPY requirements.txt .
   146|RUN pip install --no-cache-dir -r requirements.txt
   147|
   148|COPY . .
   149|
   150|RUN useradd -r -s /bin/false appuser
   151|RUN chown -R appuser:appuser /app
   152|
   153|USER appuser
   154|
   155|EXPOSE 8080
   156|
   157|HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
   158|    CMD curl -f http://localhost:8080/health || exit 1
   159|
   160|CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0"]
   161|```
   162|
   163|---
   164|
   165|## 🧪 练习题
   166|
   167|### 练习 1：镜像瘦身
   168|
   169|优化以下 Dockerfile：
   170|```dockerfile
   171|FROM ubuntu:22.04
   172|RUN apt-get update && apt-get install -y python3 python3-pip gcc
   173|RUN pip3 install flask gunicorn
   174|COPY . /app
   175|```
   176|
   177|<details>
   178|<summary>答案</summary>
   179|
   180|```dockerfile
   181|FROM python:3.11-slim
   182|COPY requirements.txt .
   183|RUN pip install --no-cache-dir -r requirements.txt
   184|COPY . /app
   185|EXPOSE 5000
   186|CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
   187|```
   188|</details>
   189|
   190|---
   191|
   192|## 📚 扩展阅读
   193|
   194|- [Docker 镜像文档](https://docs.docker.com/engine/reference/commandline/images/)
   195|- [多阶段构建](https://docs.docker.com/build/building/multi-stage/)
   196|

## 🏗️ 实战：镜像瘦身与优化

### 镜像瘦身前后对比

```
优化前（~900MB）：
FROM python:3.11
RUN apt-get update && apt-get install -y gcc
COPY . /app
RUN pip install -r requirements.txt

优化后（~120MB）：
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
```

### 多阶段构建实战

```dockerfile
# Go 应用
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server .

FROM alpine:3.18
RUN apk --no-cache add ca-certificates tzdata
COPY --from=builder /server /server
USER nobody
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s \
    CMD wget -qO- http://localhost:8080/health || exit 1
ENTRYPOINT ["/server"]
```

### 构建缓存详解

```
Docker 构建缓存机制：
1. 每条 Dockerfile 指令创建一层
2. 如果指令和上下文未变，使用缓存
3. 某层缓存失效后，后续所有层重新构建
4. COPY/ADD 指令检查文件内容 hash

优化策略：
- 将不变的指令放前面（FROM, ENV, WORKDIR）
- 将经常变化的指令放后面（COPY .）
- 先复制依赖文件，安装依赖，再复制代码
```

### .dockerignore

```
# .dockerignore 文件
.git
.gitignore
__pycache__
*.pyc
*.pyo
.env
.env.*
tests/
*.md
Dockerfile
.dockerignore
node_modules/
```

## 🧪 练习题

### 练习 1：分析镜像层

<details>
<summary>答案</summary>

```bash
docker history nginx:latest
docker history --no-trunc nginx:latest
docker inspect nginx:latest | grep -A 20 "RootFS"
```
</details>

### 练习 2：构建多架构镜像

<details>
<summary>答案</summary>

```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:v1 --push .
```
</details>

---

## 📚 扩展阅读

- [Docker 镜像文档](https://docs.docker.com/engine/reference/commandline/images/)
- [多阶段构建](https://docs.docker.com/build/building/multi-stage/)
- [Docker Hub 官方镜像](https://hub.docker.com/)
