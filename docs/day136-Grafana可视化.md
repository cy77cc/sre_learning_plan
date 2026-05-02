# Day 136: Grafana 可视化

> 📅 日期：2026-05-04
> 📖 学习主题：Grafana 可视化
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 能安装和配置 Grafana
- 能创建仪表盘

---

## 📖 Grafana

### 安装

```bash
docker run -d -p 3000:3000 grafana/grafana
```

### 数据源

```
Prometheus
MySQL
Loki
Jaeger
Elasticsearch
```

### RED 方法仪表盘

```
Rate（速率）— 每秒请求数
Errors（错误）— 每秒错误数
Duration（延迟）— 请求延迟分布
```

---

## 📚 扩展阅读

- [Grafana 文档](https://grafana.com/docs/)
