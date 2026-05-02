# Day 135: PromQL 查询语言

> 📅 日期：2026-05-04
> 📖 学习主题：PromQL 查询语言
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 PromQL 基本语法
- 能编写常用查询

---

## 📖 PromQL

### 基本查询

```promql
# 瞬时向量
http_requests_total

# 带标签过滤
http_requests_total{method="GET", status="200"}

# 正则匹配
http_requests_total{status=~"5.."}
```

### 函数

```promql
# 速率
rate(http_requests_total[5m])

# 增加量
increase(http_requests_total[1h])

# 聚合
sum(rate(http_requests_total[5m])) by (job)

# 百分位
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

---

## 📚 扩展阅读

- [PromQL 文档](https://prometheus.io/docs/prometheus/latest/querying/basics/)
