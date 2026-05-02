# Day 82: 实战项目 — Docker 化 Web 应用

> 📅 日期：2026-05-03
> 📖 学习主题：实战项目：Docker 化 Web 应用
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 将完整 Web 应用 Docker 化
- 掌握多容器编排
- 理解开发环境 vs 生产环境的差异

---

## 🏗️ 项目：Flask + Redis + Nginx

### 1. 应用代码

```python
# app.py
from flask import Flask
import redis
import os

app = Flask(__name__)
redis_host = os.environ.get("REDIS_HOST", "localhost")
r = redis.Redis(host=redis_host, port=6379)

@app.route("/")
def index():
    count = r.incr("visits")
    return f"Visits: {count}"

@app.route("/health")
def health():
    r.ping()
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### 3. Nginx 配置

```nginx
server {
    listen 80;
    location / {
        proxy_pass http://app:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. docker-compose.yml

```yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app

volumes:
  redis_data:
```

### 5. 运行

```bash
docker compose up -d
docker compose ps
docker compose logs -f app
```

---

## 📚 扩展阅读

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [多容器应用](https://docs.docker.com/compose/gettingstarted/)
