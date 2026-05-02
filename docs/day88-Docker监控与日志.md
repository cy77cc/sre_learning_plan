# Day 88: Docker 监控与日志

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 监控与日志
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Docker 日志驱动
- 能用 cAdvisor + Prometheus 监控容器
- 理解容器日志管理策略

---

## 📖 日志管理

### 1. 日志驱动

```bash
# 查看当前日志驱动
docker info | grep "Logging Driver"

# 配置日志驱动
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 2. 常用日志驱动

| 驱动 | 说明 |
|------|------|
| json-file | 默认，JSON 格式存储 |
| syslog | 发送到 syslog |
| journald | 发送到 systemd journal |
| fluentd | 发送到 Fluentd |
| awslogs | 发送到 CloudWatch |
| gelf | 发送到 Graylog |

### 3. 监控方案

```bash
# cAdvisor — 容器资源监控
docker run -d \
    --name=cadvisor \
    -p 8080:8080 \
    -v /:/rootfs:ro \
    -v /var/run:/var/run:ro \
    -v /sys:/sys:ro \
    -v /var/lib/docker/:/var/lib/docker:ro \
    gcr.io/cadvisor/cadvisor

# 配合 Prometheus + Grafana
# 完整的容器监控栈
```

---

## 📚 扩展阅读

- [Docker 日志文档](https://docs.docker.com/config/containers/logging/)
- [cAdvisor](https://github.com/google/cadvisor)
