# Day 112: CloudWatch 监控

> 📅 日期：2026-05-04
> 📖 学习主题：CloudWatch 监控
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 CloudWatch 的三大功能
- 能配置告警和日志

---

## 📖 CloudWatch

### 1. Metrics

```bash
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=i-xxx \
    --start-time 2026-01-01T00:00:00Z \
    --end-time 2026-01-01T01:00:00Z \
    --period 300 --statistics Average
```

### 2. Alarms

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name high-cpu \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average --period 300 --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:123456789:alerts
```

### 3. Logs

```bash
aws logs create-log-group --log-group-name /app/myapp
aws logs put-retention-policy --log-group-name /app/myapp --retention-in-days 30
```

---

## 📚 扩展阅读

- [CloudWatch 文档](https://docs.aws.amazon.com/cloudwatch/)
