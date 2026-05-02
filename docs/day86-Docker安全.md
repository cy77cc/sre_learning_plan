# Day 86: Docker 安全

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 安全
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Docker 安全风险点
- 掌握容器安全加固方法
- 能扫描镜像漏洞

---

## 📖 安全最佳实践

### 1. 镜像安全

```bash
# 扫描漏洞
docker scout cve myapp:latest
trivy image myapp:latest
grype myapp:latest
```

### 2. 运行时安全

```bash
# 不用 root
USER appuser

# 只读根文件系统
docker run --read-only myapp

# 限制能力
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp

# 安全选项
docker run \
    --security-opt no-new-privileges \
    --security-opt seccomp=default.json \
    myapp
```

### 3. 网络安全

```bash
# 隔离网络
docker network create --internal secure-net

# 限制端口暴露
docker run -p 127.0.0.1:8080:80 myapp
```

### 4. 密钥管理

```bash
# 不要用 ENV 存密码
# 使用 Docker secrets
echo "mypassword" | docker secret create db_password -
docker service create --secret db_password myapp
```

### 5. 审计

```bash
# 启用审计日志
# 监控容器事件
docker events
```

---

## 📚 扩展阅读

- [Docker 安全文档](https://docs.docker.com/security/)
- [Trivy 漏洞扫描](https://github.com/aquasecurity/trivy)
