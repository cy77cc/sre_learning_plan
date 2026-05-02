# Day 152: CI 中构建和推送镜像

> 📅 日期：2026-05-05
> 📖 学习主题：CI 中构建和推送镜像
> ⏰ 计划学习时间：2-3 小时

---

## 📖 CI 构建镜像

```yaml
- name: Build and Push
  run: |
    docker build -t registry.example.com/myapp:$TAG .
    docker push registry.example.com/myapp:$TAG
```

---

## 📚 扩展阅读

- [Docker CI/CD](https://docs.docker.com/ci-cd/)
