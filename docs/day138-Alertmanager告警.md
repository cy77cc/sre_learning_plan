# Day 138: Alertmanager 告警

> 📅 日期：2026-05-04
> 📖 学习主题：Alertmanager 告警
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Alertmanager 配置
- 能设置告警路由

---

## 📖 Alertmanager

### 告警规则

```yaml
groups:
  - name: example
    rules:
      - alert: HighCPU
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
```

### 路由

```yaml
route:
  group_by: ['alertname']
  receiver: 'slack'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
```

---

## 📚 扩展阅读

- [Alertmanager 文档](https://prometheus.io/docs/alerting/)
