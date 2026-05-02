# Day 140: 日志收集基础 — ELK

> 📅 日期：2026-05-05
> 📖 学习主题：日志收集基础 — ELK
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 ELK Stack 架构
- 能部署 ELK

---

## 📖 ELK

### 架构

```
Filebeat/Fluentd → Logstash → Elasticsearch → Kibana
```

### 部署

```bash
docker run -d -p 9200:9200 -p 9300:9300 elasticsearch:8.11.0
docker run -d -p 5601:5601 kibana:8.11.0
```

---

## 📚 扩展阅读

- [ELK 文档](https://www.elastic.co/guide/)
