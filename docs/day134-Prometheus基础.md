# Day 134: Prometheus 基础

> 📅 日期：2026-05-04
> 📖 学习主题：Prometheus 基础
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Prometheus 架构
- 掌握四种指标类型
- 能安装和配置 Prometheus

---

## 📖 Prometheus 架构

```
Targets (Exporter) → Pull → Prometheus → PromQL → Grafana
                                      ↓
                                 TSDB (存储)
                                      ↓
                               Alertmanager (告警)
```

## 四种指标类型

| 类型 | 说明 | 示例 |
|------|------|------|
| Counter | 只增不减 | 请求总数 |
| Gauge | 可增可减 | CPU 使用率 |
| Histogram | 分布统计 | 请求延迟分布 |
| Summary | 分位数统计 | P99 延迟 |

## 安装

```bash
docker run -d -p 9090:9090 \
    -v /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus
```

## 配置

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

---

## 📚 扩展阅读

- [Prometheus 文档](https://prometheus.io/docs/)
