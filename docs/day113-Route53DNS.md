# Day 113: Route 53 DNS

> 📅 日期：2026-05-04
> 📖 学习主题：Route 53 DNS
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Route 53 的路由策略
- 能配置 DNS 记录

---

## 📖 Route 53

### 路由策略

| 策略 | 说明 |
|------|------|
| Simple | 单值 |
| Weighted | 权重分配 |
| Latency | 最低延迟 |
| Failover | 故障转移 |
| Geolocation | 基于地理位置 |

### 配置

```bash
aws route53 create-hosted-zone --name example.com --caller-reference unique-id
aws route53 change-resource-record-sets --hosted-zone-id ZXXX --change-batch file://changes.json
```

---

## 📚 扩展阅读

- [Route 53 文档](https://docs.aws.amazon.com/route53/)
